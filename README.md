# Keiko
Local AI assistant with voice and gesture control — talk to it, show it gestures, control your PC hands-free


----------------
The project is in process
----------------


--------
Future architecture
--------

```
keiko/
│
├── main.py
│
├── core/
│   ├── __init__.py
│   ├── events.py
│   ├── state.py
│   └── orchestrator.py
│
├── voice/
│   ├── __init__.py
│   ├── wakeword.py
│   ├── stt.py
│   └── tts.py
│
├── gestures/
│   ├── __init__.py
│   ├── tracker.py
│   ├── classifier.py
│   └── custom.py
│
├── tools/
│   ├── __init__.py
│   ├── apps.py
│   └── screenshot.py
│
├── llm/
│   ├── __init__.py
│   └── client.py
│
├── rag/
│   ├── __init__.py
│   └── search.py
│
├── ui/
│   ├── __init__.py
│   └── overlay.py
│
├── data/
│   ├── gestures/
│   └── documents/
│
└── config.py
```
