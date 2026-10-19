import re
from collections import deque
import numpy as np
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
CHUNK_SECONDS = 0.1
PRE_ROLL_SECONDS = 0.4
END_SILENCE_SECONDS = 0.5
MIN_SPEECH_SECONDS = 0.35
MAX_SEGMENT_SECONDS = 6.0
MIN_RMS = 200
NOISE_MULTIPLIER = 3.0
CALIBRATION_SECONDS = 1.0

WAKE_RE = re.compile(
    r"\b(?:hey|hay|hi|hei|ay)\s*"
    r"(?:keiko|keyko|keico|kayko|kaiko|keko|kiko|kayco|kei\s*ko|kay\s*ko|"
    r"key\s*ko|kay\s*co|ke\s*ko|ki\s*ko)\b"
)

_noise_floor = None


def get_voice_threshold() -> float:
    base = _noise_floor if _noise_floor is not None else 0.0
    return max(MIN_RMS, base * NOISE_MULTIPLIER)


PROMPT = "Hey Keiko."


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", text.lower()).strip()


def _rms(audio: np.ndarray) -> float:
    if audio.size == 0:
        return 0.0
    a = audio.astype(np.float32)
    return float(np.sqrt(np.mean(a * a)))


def _transcribe(whisper: WhisperModel, audio_int16: np.ndarray) -> str:
    audio = audio_int16.astype(np.float32) / 32768.0
    segments, _ = whisper.transcribe(
        audio,
        language="en",
        beam_size=1,
        temperature=0.0,
        vad_filter=False,
        condition_on_previous_text=False,
        without_timestamps=True,
        initial_prompt=PROMPT,
    )
    return " ".join(s.text.strip() for s in segments).strip()


def match_wake_word(text: str):
    norm = _normalize(text)
    m = WAKE_RE.search(norm)
    if not m:
        return False, ""
    return True, norm[m.end():].strip()


def wait_for_wake_word(whisper: WhisperModel, get_audio_chunk) -> str:
    print("\nWaiting for 'Hey, Keiko'...")

    pre_roll = deque(maxlen=int(PRE_ROLL_SECONDS / CHUNK_SECONDS))
    segment = []
    in_speech = False
    silence = 0.0
    speech = 0.0

    global _noise_floor
    calib_left = CALIBRATION_SECONDS if _noise_floor is None else 0.0
    calib_levels = []

    while True:
        chunk = get_audio_chunk(timeout=1.0)
        if chunk is None:
            continue

        level = _rms(chunk)
        dur = len(chunk) / SAMPLE_RATE
        if _noise_floor is None:
            calib_levels.append(level)
            calib_left -= dur
            if calib_left <= 0:
                _noise_floor = float(np.median(calib_levels))
            continue

        is_voice = level >= get_voice_threshold()
        if not in_speech and not is_voice:
            _noise_floor = 0.98 * _noise_floor + 0.02 * level
        if not in_speech:
            if is_voice:
                in_speech = True
                segment = list(pre_roll) + [chunk]
                speech = dur
                silence = 0.0
            else:
                pre_roll.append(chunk)
            continue

        segment.append(chunk)
        if is_voice:
            speech += dur
            silence = 0.0
        else:
            silence += dur

        total = len(segment) * CHUNK_SECONDS
        if silence >= END_SILENCE_SECONDS or total >= MAX_SEGMENT_SECONDS:
            audio = np.concatenate(segment)
            in_speech = False
            segment = []
            pre_roll.clear()

            if speech < MIN_SPEECH_SECONDS:
                continue

            text = _transcribe(whisper, audio)
            if text:
                print(f"\rHeard: {text:<60}", end="")

            found, rest = match_wake_word(text)
            if found:
                print("\nWake phrase detected!")
                return rest

if __name__ == "__main__":
    import queue

    import sounddevice as sd

    q = queue.Queue(maxsize=200)

    def cb(indata, frames, t, status):
        try:
            q.put_nowait(indata[:, 0].copy())
        except queue.Full:
            try:
                q.get_nowait()
                q.put_nowait(indata[:, 0].copy())
            except (queue.Empty, queue.Full):
                pass

    def get_chunk(timeout=1.0):
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            return None

    model = WhisperModel("base.en", device="cpu", compute_type="int8")
    with sd.InputStream(samplerate=SAMPLE_RATE, blocksize=1600, channels=1,
                        dtype="int16", callback=cb):
        while True:
            rest = wait_for_wake_word(model, get_chunk)
            print(f"-> after wake word: {rest!r}")
