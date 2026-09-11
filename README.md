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
|-- main.py
│
|-- core/ (ready)
│   |-- events.py 
│   |--state.py
│   |-- orchestrator.py
│
|-- voice/
│   |-- wakeword.py
│   |-- stt.py
│   |-- tts.py
│
|-- gestures/
│   |-- tracker.py
│   |-- classifier.py
│   |--custom.py
│
|-- tools/
│   |-- apps.py
│   |-- base.py
|   |-- user.py
│
|-- llm/
│   |-- client.py
│
|-- rag/
│   |-- search.py
│
|-- ui/
│   |-- overlay.py
│
|--data/
│   |-- gestures/
│   |-- documents/
│
|-- config.py
```
