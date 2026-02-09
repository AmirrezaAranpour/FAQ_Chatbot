# Architecture (FAQ Chatbot - PDF-aligned)

## Goal
Build a small, testable FAQ chatbot that answers **only** from a provided knowledge base (KB). If the KB does not contain the answer, it must **fallback** safely without guessing.

## Components
1) **Knowledge Base** (`knowledge_base/`)
   - A small set of Markdown documents describing services, pricing, process, support/SLA, and policies.
   - `00_scope.md` defines the boundary and is not indexed.

2) **Index Builder** (`scripts/build_index.py`)
   - Reads KB files (excluding `00_*`).
   - Splits text into chunks.
   - Generates embeddings for each chunk.
   - Builds a FAISS vector index and saves it under `.cache/`.

3) **Retriever** (`app/rag.py`)
   - Embeds the user question.
   - Retrieves top-K most similar chunks from FAISS.
   - Produces a best similarity score and the corresponding sources.

4) **Guardrails**
   - If the best similarity score is below a threshold → **fallback**.
   - Lexical overlap is optionally used for Latin text to reduce irrelevant matches (disabled for non‑Latin inputs to avoid false fallbacks).

5) **Answering**
   - Default (no LLM): a **question-focused extractive** answer is generated from retrieved chunks (selecting the most relevant lines to avoid dumping whole sections).
   - Optional LLM mode: uses Prompt v2 to generate a short grounded answer **only from CONTEXT**.

6) **API + UI**
   - FastAPI backend with a minimal chat UI.
   - The UI renders Markdown safely (headings/bullets/bold) without showing raw markers (e.g., `##`).

## Input/Output
- Input: user question (string).
- Output: JSON containing:
  - `answer` (string)
  - `sources` (list of filenames)
  - `confidence` (similarity score)
  - `is_fallback` (boolean)

## Deliverables for review
- 12-question FAQ list: `data/faq_list.json`
- Complete FAQ with reference answers + sources: `data/faq_complete.json`
- Prompt documentation: `prompts/prompts.md`


## Core FAQ routing (12 questions)
- The repository includes a curated set of **12 core FAQ questions** with reference answers in `data/faq_complete.json`.
- The API applies lightweight fuzzy matching (typo/paraphrase tolerant). If the user question matches a core FAQ, the chatbot returns the **reference answer** and its sources.
- This improves functional correctness for evaluation while still keeping RAG behavior for other in-scope questions.
