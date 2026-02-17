# FAQ Chatbot (ARV Digital Services)

A lightweight FAQ chatbot that answers **only** from the local markdown knowledge base (`knowledge_base/`).
It includes a clean, dark web UI with a **guided prompt panel** and clear response modes.

## Key features

- **Grounded answers**: responds using only the KB and shows **source filenames**
- **Clarify mode**: asks a short follow‑up when the question is in‑scope but too vague
- **Safe fallback**: refuses out‑of‑scope or unsupported questions (no guessing)
- **Simple local RAG**: builds a small local index from markdown files (no heavy vector DB)
- **Web UI**: dark theme, mode badges (grounded / clarify / fallback / error), copy‑friendly answers

---

## Project structure

```
.
├─ app/
│  ├─ main.py            # FastAPI server (UI + /chat endpoint)
│  ├─ rag.py             # Index loading + retrieval
│  ├─ llm.py             # Answer/clarify/fallback logic (prompting)
│  └─ config.py          # Settings (thresholds, paths, etc.)
├─ knowledge_base/       # Markdown KB (the only source of truth)
├─ scripts/
│  ├─ build_index.py     # Build/rebuild the local index
│  ├─ smoke_test.py      # Local CLI smoke tests
│  └─ smoke_test_http.py # HTTP smoke tests against a running server
├─ templates/            # Server-rendered HTML
└─ static/               # CSS/JS (UI)
```

---

## Requirements

- Python **3.10+** recommended (works best on 3.10–3.12)
- No GPU required

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Build the index (ingest the KB)

```bash
python scripts/build_index.py
```

You should see a message similar to:

- `Index built: {'docs': X, 'chunks': Y, 'dim': 384}`

---

## Run

```bash
uvicorn app.main:app --reload --port 8001
```

Open: `http://127.0.0.1:8001`

If you see **Address already in use**, pick a different port (e.g. `--port 8002`).

---

## How to use the UI

Left panel includes:

- **Guided prompts**: choose a Topic + Example, then **Insert** (fills input) or **Ask now**
- **Modes legend**: what Grounded / Clarify / Fallback means
- **Tips**: how to ask better questions

> If the UI looks “stuck” after changes, hard refresh the page  
> Windows/Linux: `Ctrl + Shift + R` — macOS: `Cmd + Shift + R`

---

## API

### `POST /chat`

Request:

```json
{ "question": "..." }
```

Response:

```json
{
  "answer": "…",
  "mode": "grounded",
  "confidence": 0.78,
  "sources": ["pricing.md"]
}
```

- `mode` is one of: `grounded`, `clarify`, `fallback`, `error`
- `sources` are KB filenames used to answer

### `POST /reindex`

Rebuilds the index from `knowledge_base/` (same as running `scripts/build_index.py`).

---

## Knowledge base rules (important)

- The KB (`knowledge_base/*.md`) is the **only** knowledge source.
- If something is not in the KB, the assistant must **fallback** (no invented details).
- For vague in-scope questions, the assistant may ask **one** short clarifying question.

---

## Testing

### CLI smoke test

```bash
python scripts/smoke_test.py
```

### HTTP smoke test

1) Start the server  
2) Run:

```bash
python scripts/smoke_test_http.py --base-url http://127.0.0.1:8001
```

---

## Troubleshooting

- **500 errors**: check the terminal stack trace; usually a missing import or a stale cache.
- **UI changes not visible**: hard refresh (`Ctrl/Cmd + Shift + R`).  
  You can also clear the browser cache or restart `uvicorn`.
- **Index seems outdated**: run `python scripts/build_index.py` again.

---

