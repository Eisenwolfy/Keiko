# Keiko
Personal Local AI Agent


----------------
Architecture
----------------


]personal-agent/
│
├── app/
│   ├── main.py
│   │
│   ├── agent/
│   │   ├── agent.py
│   │   ├── prompts.py
│   │   └── planner.py
│   │
│   ├── memory/
│   │   ├── short_term.py
│   │   ├── long_term.py
│   │   └── vector_store.py
│   │
│   ├── tools/
│   │   ├── calculator.py
│   │   ├── web.py
│   │   ├── python.py
│   │   └── files.py
│   │
│   └── llm/
│       └── ollama.py
│
├── data/
│   └── memory.db
│
├── frontend/
│
├── tests/
│
├── requirements.txt
└── README.md
