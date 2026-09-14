import speech_recognition as sr
from orchestrator import Orchestrator
from events import VoiceEventType, VoiceEvent
import asyncio

r = sr.Recognizer()
orch = Orchestrator()

print('yo')
while True:
    with sr.Microphone() as scr:
        try:
            cmd = r.recognize_google(r.listen(scr), language="en-US")
            event = VoiceEvent(type=VoiceEventType.SPEECH, text=cmd, confidence=1.0)
            asyncio.run(orch.handle_event(event))

        except:
            pass
