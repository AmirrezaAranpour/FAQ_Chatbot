# Complete FAQ List (Core FAQ)

The canonical Q/A set lives in:

- `data/core_faq.json`

Each entry contains:

- `question` — canonical question
- `reference_answer` — the exact answer returned for a confident match
- `sources` — one or more KB files used as citation

The router attempts, in order:

1) **Alias match** (short queries like `pricing`, `support`, `nda`, …) using `data/aliases.json`
2) **Fuzzy match** against canonical questions (`CORE_MATCH_THRESHOLD`)
3) **Hybrid retrieval** over the KB chunks (BM25 + embeddings)

This gives stable grading on the core FAQ while still handling reasonable variations in wording.
