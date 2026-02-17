# System Architecture (FAQ Chatbot)

This document explains the end-to-end architecture and how a user question flows through the system.

## 1) Overall architecture

**Frontend (UI)**
- A lightweight single-page web UI (static HTML/CSS/JS).
- Sends the user question to the backend via `POST /chat`.
- Renders:
  - The answer text
  - The response type (**grounded / clarify / fallback / error**)
  - Confidence score
  - Sources (file names from the knowledge base)

**Backend (API)**
- A small FastAPI service exposes:
  - `POST /chat` (main chatbot endpoint)
  - `GET /health` (basic health check)

**Knowledge Source (KB)**
- `knowledge_base/` contains the authoritative, limited scope content.
- `data/core_faq.json` contains the canonical FAQ set (>= 10) with **final answers** + **sources**.

**Retrieval & Index**
- `scripts/build_index.py` ingests `knowledge_base/` and builds an embeddings index in `.cache/`.
- On every question, the backend retrieves the most relevant KB chunk(s).

## 2) Question processing flow

1. **Input normalization**
   - Trim whitespace, collapse repeated spaces, basic normalization.
   - Reject empty input.

2. **Safety & scope checks**
   - If the question is clearly out-of-scope (e.g., medical/legal advice, real-time prices), return a **safe fallback**.

3. **Ambiguity / vagueness handling (Clarify)**
   - If the input is *too vague* (e.g., “How much will it be?”, “What’s included?”) the backend returns a **clarifying question** asking the user to specify the service/topic.

4. **Core FAQ match (deterministic layer)**
   - The backend attempts to match the question to one of the canonical FAQs in `data/core_faq.json` using:
     - normalization
     - keyword + phrase overlap
     - typo-tolerant matching (lightweight)
   - If the match is strong enough, the system returns that **final answer** (with its sources) directly.

5. **RAG retrieval (vector search)**
   - If no strong core match is found, the system performs retrieval:
     - embed the user question
     - search the vector index
     - compute similarity score(s)

6. **Response control decision**
   - If the best similarity is **>= threshold** → return **grounded** answer, citing sources.
   - If the best similarity is **< threshold** → return **fallback**.

7. **UI rendering**
   - The UI displays the answer and highlights the response type and confidence.

## 3) RAG design

**Ingestion**
- KB files are read from `knowledge_base/`.
- Content is chunked into small sections.
- Each chunk is embedded using a compact sentence embedding model.

**Indexing**
- The vector index and chunk metadata are stored under `.cache/`.
- Index build is reproducible by re-running `python scripts/build_index.py`.

**Retrieval**
- The backend retrieves top-k chunks and keeps only those that are relevant enough.
- The final response is composed strictly from:
  - the matched canonical FAQ answer, or
  - the retrieved KB chunk(s)

## 4) Fallback logic

Fallback is intentionally **predictable** and **non-misleading**:

- The chatbot never guesses.
- For out-of-scope or low-confidence queries, it returns a short message explaining that the information is not in the KB and suggests rephrasing or contacting support.

This aligns with the task’s requirement that responses must not be speculative or fabricated.
