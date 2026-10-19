import os
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="torch")
warnings.filterwarnings("ignore", category=FutureWarning, module="torch")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

try:
    import torch
except ImportError:
    pass

import queue
import re
import threading
import time

import numpy as np
import ollama
import sounddevice as sd
from faster_whisper import WhisperModel

import wake_word
from wake_word import wait_for_wake_word

OLLAMA_MODEL = "gemma3n:e4b"

SAMPLE_RATE = 16000
CHUNK_SIZE = 1600

WAKE_MODEL = "base.en"
COMMAND_MODEL = "base"
COMMAND_LANGUAGE = "en"

SESSION_TIMEOUT = 30.0
SILENCE_SECONDS = 1.0
MAX_COMMAND_SECONDS = 20

TTS_ENGINE = "kokoro"
KOKORO_LANG = "a"
KOKORO_VOICE = "af_heart"
KOKORO_DEVICE = "cpu"
KOKORO_SPEED = 1.05
KOKORO_PITCH = 1.15
PYTTSX3_RATE = 180

GOODBYE_RE = re.compile(r"\b(?:goodbye|good bye|bye)\b(?:\s+(?:keiko|keko|kiko))?")

SYSTEM_PROMPT = (
    "You are Keiko, a cheerful, warm personal AI assistant. "
    "Answer naturally and concisely. Your answers will be spoken aloud, "
    "so avoid markdown, lists and emojis."
)

audio_queue = queue.Queue(maxsize=200)


def audio_callback(indata, frames, time_info, status):
    chunk = indata[:, 0].copy()
    try:
        audio_queue.put_nowait(chunk)
    except queue.Full:
        try:
            audio_queue.get_nowait()
            audio_queue.put_nowait(chunk)
        except (queue.Empty, queue.Full):
            pass


def get_audio_chunk(timeout=1.0):
    try:
        return audio_queue.get(timeout=timeout)
    except queue.Empty:
        return None


def clear_audio_queue():
    while True:
        try:
            audio_queue.get_nowait()
        except queue.Empty:
            break


def rms_level(audio):
    if len(audio) == 0:
        return 0.0
    a = audio.astype(np.float32)
    return float(np.sqrt(np.mean(a * a)))


class Speaker:
    def __init__(self, rate=PYTTSX3_RATE):
        self.rate = rate
        self.backend = "pyttsx3"
        self.pipeline = None

        if TTS_ENGINE == "kokoro":
            try:
                from kokoro import KPipeline
                try:
                    self.pipeline = KPipeline(lang_code=KOKORO_LANG, repo_id="hexgrad/Kokoro-82M", device=KOKORO_DEVICE)
                except TypeError:
                    self.pipeline = KPipeline(lang_code=KOKORO_LANG)
                for _ in self.pipeline("Hello.", voice=KOKORO_VOICE):
                    pass
                self.backend = "kokoro"
            except Exception as error:
                self.pipeline = None
                print(f"Kokoro unavailable ({error}).\n"
                      "Falling back to pyttsx3 voice.")

        print(f"TTS backend: {self.backend}")

        self._q = queue.Queue()
        self._stop = False
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()


    def say(self, text):
        text = text.strip()
        if text:
            print(f"\nKeiko: {text}")
            self._q.put(text)

    def wait(self):
        self._q.join()
        time.sleep(0.25)
        clear_audio_queue()

    def close(self):
        self._stop = True
        self._q.put(None)

    def _worker(self):
        if self.backend == "pyttsx3":
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception:
                try:
                    import comtypes
                    comtypes.CoInitialize()
                except Exception:
                    pass

        while not self._stop:
            item = self._q.get()
            if item is None:
                self._q.task_done()
                break

            batch = [item]
            while True:
                try:
                    nxt = self._q.get_nowait()
                except queue.Empty:
                    break
                if nxt is None:
                    self._stop = True
                    self._q.task_done()
                    break
                batch.append(nxt)

            try:
                text = " ".join(batch)
                if self.backend == "kokoro":
                    self._play_kokoro(text)
                else:
                    self._play_pyttsx3(text)
            except Exception as error:
                print(f"TTS error: {error}")
            finally:
                for _ in batch:
                    self._q.task_done()

    def _play_kokoro(self, text):
        pcm_q = queue.Queue(maxsize=8)

        def produce():
            try:
                for _, _, audio in self.pipeline(
                        text, voice=KOKORO_VOICE, speed=KOKORO_SPEED,
                        split_pattern=r"\n+"):
                    if audio is None:
                        continue
                    if hasattr(audio, "detach"):
                        audio = audio.detach().cpu().numpy()
                    pcm_q.put(np.asarray(audio, dtype=np.float32))
            except Exception as error:
                print(f"Kokoro error: {error}")
            finally:
                pcm_q.put(None)

        threading.Thread(target=produce, daemon=True).start()

        with sd.OutputStream(samplerate=int(24000 * KOKORO_PITCH),
                             channels=1, dtype="float32") as out:
            while True:
                pcm = pcm_q.get()
                if pcm is None:
                    break
                out.write(pcm.reshape(-1, 1))

    def _play_pyttsx3(self, text):
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", self.rate)
        engine.say(text)
        engine.runAndWait()
        try:
            engine.stop()
        except Exception:
            pass
        del engine


def speak(tts, text):
    tts.say(text)
    tts.wait()


def _tone(freqs, seconds=0.1, volume=0.2):
    try:
        parts = []
        for f in freqs:
            t = np.linspace(0, seconds, int(SAMPLE_RATE * seconds),
                            endpoint=False)
            parts.append(volume * np.sin(2 * np.pi * f * t))
        tone = (np.concatenate(parts) * 32767).astype(np.int16)
        sd.play(tone, SAMPLE_RATE)
        sd.wait()
    except Exception:
        pass
    clear_audio_queue()


def beep():
    _tone([660, 880])

def sleep_beep():
    _tone([660, 440])



def initialize():
    print("Loading Whisper models...")
    wake_model = WhisperModel(WAKE_MODEL, device="cpu", compute_type="int8")
    if COMMAND_MODEL == WAKE_MODEL:
        command_model = wake_model
    else:
        command_model = WhisperModel(COMMAND_MODEL, device="cpu",
                                     compute_type="int8")

    print("Initializing text-to-speech")
    tts = Speaker()

    print("Checking Ollama")
    result = ollama.list()
    names = [getattr(m, "model", None) or getattr(m, "name", "")
             for m in result.models]
    if not any(n == OLLAMA_MODEL or n.startswith(OLLAMA_MODEL + ":")
               for n in names):
        raise RuntimeError(
            f"Cannot find {OLLAMA_MODEL} in Ollama.\n"
            "Run 'ollama list' and update OLLAMA_MODEL."
        )

    print("All components initialized.")
    return wake_model, command_model, tts


def transcribe(model, audio):
    if len(audio) == 0:
        return ""
    audio_f = audio.astype(np.float32) / 32768.0
    segments, _ = model.transcribe(
        audio_f,
        language=COMMAND_LANGUAGE,
        vad_filter=True,
        beam_size=3,
        condition_on_previous_text=False,
    )
    return " ".join(s.text.strip() for s in segments).strip()


def normalize(text):
    return re.sub(r"[^a-z0-9\s]", " ", text.lower()).strip()


def listen_command(model, deadline):
    chunks = []
    started = False
    silent = 0.0
    total = 0.0

    while True:
        if not started and time.monotonic() >= deadline:
            return ""
        if total >= MAX_COMMAND_SECONDS:
            break

        chunk = get_audio_chunk(timeout=0.3)
        if chunk is None:
            continue

        dur = len(chunk) / SAMPLE_RATE
        is_voice = rms_level(chunk) >= wake_word.get_voice_threshold()

        if not started:
            chunks.append(chunk)
            chunks = chunks[-4:]
            if is_voice:
                started = True
                silent = 0.0
                total = 0.0
            continue

        total += dur
        chunks.append(chunk)
        if is_voice:
            silent = 0.0
        else:
            silent += dur
            if silent >= SILENCE_SECONDS:
                break

    if not started:
        return ""
    return transcribe(model, np.concatenate(chunks))

SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

def ask_and_speak(tts, messages):
    full = []
    buf = ""
    stream = ollama.chat(model=OLLAMA_MODEL, messages=messages, stream=True)

    for part in stream:
        piece = part["message"]["content"]
        full.append(piece)
        buf += piece

        parts = SENTENCE_END.split(buf)
        for sentence in parts[:-1]:
            tts.say(sentence)
        buf = parts[-1]

    tts.say(buf)
    tts.wait()

    return "".join(full).strip()


def voice_session(command_model, tts, first_command=""):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    pending = first_command.strip()

    if not pending:
        beep()

    deadline = time.monotonic() + SESSION_TIMEOUT
    print(f"\nListening... (sleep after {SESSION_TIMEOUT:.0f}s of silence)")

    while True:
        command = pending or listen_command(command_model, deadline)
        pending = ""

        if not command:
            if time.monotonic() >= deadline:
                print("\nNo command, going back to sleep.")
                sleep_beep()
                return
            continue

        print(f"\nYou: {command}")

        if GOODBYE_RE.search(normalize(command)):
            speak(tts, "Goodbye!")
            return

        messages.append({"role": "user", "content": command})

        try:
            answer = ask_and_speak(tts, messages)
        except Exception as error:
            print(f"Ollama error: {error}")
            messages.pop()
            speak(tts, "Sorry, I couldn't get a response.")
            deadline = time.monotonic() + SESSION_TIMEOUT
            continue

        messages.append({"role": "assistant", "content": answer})
        if len(messages) > 21:
            messages = [messages[0]] + messages[-20:]
        deadline = time.monotonic() + SESSION_TIMEOUT
        print(f"\nListening... (sleep after {SESSION_TIMEOUT:.0f}s of silence)")


def main():
    wake_model, command_model, tts = initialize()

    print("\nKeiko voice interface started.")
    print("Say 'Hey, Keiko' (you can add the question right away).")
    print(f"She stays awake for {SESSION_TIMEOUT:.0f}s after each answer.")
    print("Say 'Goodbye, Keiko' to put her to sleep right away.")
    print("Press Ctrl+C to exit.\n")

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, blocksize=CHUNK_SIZE,
                            channels=1, dtype="int16",
                            callback=audio_callback):
            print("Calibrating background noise - stay quiet for a second...")
            while True:
                rest = wait_for_wake_word(wake_model, get_audio_chunk)
                voice_session(command_model, tts, first_command=rest)
                clear_audio_queue()

    except KeyboardInterrupt:
        print("\nKeiko stopped.")
    finally:
        tts.close()


if __name__ == "__main__":
    main()
