# ARV FAQ Chatbot (Pro+)

A lightweight, **reviewer-friendly** FAQ chatbot for **ARV Digital Services**.
It answers **only** from the local markdown knowledge base (`knowledge_base/`) and provides clear **response control**:

- **grounded** — answer is supported by the KB and includes citations (source filenames)
- **clarify** — question is in-scope but too vague; asks one short follow‑up
- **fallback** — out-of-scope or not covered by the KB; refuses safely (no guessing)
- **error** — server-side failure; returns a safe error message

> No external browsing. No external data sources. Runs locally.

---

## What this repo contains

- **FastAPI backend** (local API + safety/grounding logic)
- **Simple web UI** (mode badge + sources, plus a Reindex button)
- **Hybrid retrieval** over KB chunks:
  - BM25 (keyword relevance)
  - deterministic embeddings (hash-based) with an **optional** Sentence-Transformers upgrade
- **Stable “core FAQ”** for consistent answers on canonical questions
- Local scripts to build the index and run test cases

---

## Quickstart

### 1) Install & run

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate

pip install -r requirements.txt

# Optional: build index once (otherwise it auto-builds on first run)
python scripts/build_index.py

uvicorn app.main:app --reload --port 8001
```

Open: `http://127.0.0.1:8001`

### 2) Rebuild the index after KB edits

- Click **Reindex** in the UI, or:

```bash
curl -X POST http://127.0.0.1:8001/reindex
```

---

## API

### `POST /chat`

Request:

```json
{ "question": "What are your pricing models?" }
```

Response (schema):

```json
{
  "answer": "...",
  "mode": "grounded|clarify|fallback|error",
  "confidence": 0.0,
  "sources": ["pricing.md"],
  "is_fallback": false
}
```

### `POST /reindex`

Rebuilds the local index from `knowledge_base/`.

---

## Project structure

```
app/
  main.py            # FastAPI app + routes
  service.py         # answer_question(): orchestrates routing + retrieval
  router.py          # alias/core matching, out-of-scope, clarify logic
  answering.py       # formatting and final answer selection
  kb/loader.py       # loads + chunks markdown docs
  retrieval/
    bm25.py          # keyword scoring
    embeddings.py    # hash embedder + optional SentenceTransformer
    index.py         # build/load index

data/
  core_faq.json       # canonical Q/A (stable outputs + sources)
  aliases.json        # short triggers (pricing, support, sla, refund, ...)
  test_cases.json     # local test suite

docs/
  PROMPTS.md          # user-facing messages (fallback/clarify) documentation
  FAQ_MAP.md          # complete FAQ list (core FAQ) and routing order
  CHANGELOG.md        # version notes

knowledge_base/
  00_scope.md         # scope boundary definition
  *.md                # policies, pricing, process, services, support

static/               # UI assets
templates/            # UI template
.cache/               # built index (safe to delete)
```

---

## How answering works

The router tries, in order:

1) **Alias match** (for short queries like `pricing`, `support`, `sla`)
2) **Core FAQ match** (fuzzy match against canonical questions)
3) **Hybrid retrieval** (BM25 + embeddings) over KB chunks

Then response control is applied:

- **Out-of-scope** → `fallback`
- **In-scope but ambiguous** → `clarify`
- **In-scope with support** → `grounded` with citations

See: `docs/FAQ_MAP.md` and `docs/PROMPTS.md`.

---

## Configuration (env vars)

You can tune behavior without touching code:

- `SIM_THRESHOLD` (default `0.50`) — minimum hybrid score to answer grounded
- `CORE_MATCH_THRESHOLD` (default `0.75`) — fuzzy match threshold for canonical questions
- `TOP_K` (default `4`) — number of chunks retrieved
- `HYBRID_ALPHA` (default `0.65`) — semantic weight vs BM25
- `FALLBACK_MESSAGE` — customize safe fallback text
- `EMPTY_MESSAGE` — text shown for blank input

Paths:

- `KB_DIR`, `CACHE_DIR`, `CORE_FAQ_PATH`, `ALIASES_PATH`

---

## Local tests

```bash
python scripts/run_tests.py
```

Edit / extend tests in `data/test_cases.json`.

---

## Troubleshooting

### UI badge colors / mode label looks wrong

Usually browser cache. Try:
- Hard refresh: **Ctrl+Shift+R** (Windows/Linux) or **Cmd+Shift+R** (macOS)
- DevTools → Network → **Disable cache** → reload

> This project also uses cache-busting (`?v={{ app_version }}`) for static assets.

### Port already in use

Run on another port:

```bash
uvicorn app.main:app --reload --port 8002
```

### Reset the index

If you changed the KB a lot:

```bash
rm -rf .cache
python scripts/build_index.py
```

---

## Optional: better embeddings (semantic retrieval)

This repo runs without heavy ML dependencies.
If you want stronger semantic matching, install:

```bash
pip install sentence-transformers
```

The code will automatically use it if available.

---

