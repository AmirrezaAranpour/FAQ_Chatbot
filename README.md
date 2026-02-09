# FAQ Chatbot (RAG) — Professional Submission

A grounded FAQ chatbot that answers using **only** the project's `knowledge_base/` and triggers a safe fallback for out-of-scope questions.

## Requirements
- Python 3.10+
- Optional: OpenAI API key OR Ollama local model

## Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Build the knowledge index (RAG ingestion)
```bash
python scripts/build_index.py
```

## Run the server
```bash
uvicorn app.main:app --reload --port 8001
```
Open: http://127.0.0.1:8001

If you see "Address already in use", change the port (e.g., 8002).

## Enable LLM answers (optional)
```bash
pip install -r requirements-llm.txt
```

### OpenAI
```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-4o-mini"
```

### Ollama (local)
```bash
ollama pull llama3.1:8b
export OLLAMA_MODEL="llama3.1:8b"
```

## Deliverables
- Runnable system: FastAPI backend + Web UI
- Knowledge source: `knowledge_base/`
- FAQ list (>=15 questions): `data/faq_list.json`
- Complete FAQ list with reference answers + source mapping (reviewer-ready): `data/faq_complete.json`
- Architecture (1–2 pages): `architecture.md`
- Prompt documentation: `prompts/prompts.md`
- Test cases: `tests.md`
- Install guide: this README

## Rebuild index after KB updates
```bash
rm -rf .cache
python scripts/build_index.py
```


## Tuning (if in-scope questions fallback)
You can tune guardrails without changing code:
```bash
export SIM_THRESHOLD=0.30
export LEX_THRESHOLD=0.02
```
Then restart the server.


## Reviewer artifacts
- Prompts (verbatim): `prompts/prompt_v1.txt`, `prompts/prompt_v2.txt`
- Prompt documentation + change-log: `prompts/prompts.md`
- Complete FAQ list with reference answers: `data/faq_complete.json`
