# Changelog

## v1.0
- Split the app into clear modules (`router`, `service`, `kb`, `retrieval`)
- Added a canonical `core_faq.json` (stable answers)
- Added aliases for short queries (`pricing`, `support`, `sla`, ...)
- Hybrid retrieval: BM25 + semantic embedding fallback (no heavy deps required)
- UI improvements + mode badges + cache-busting assets
- Added local test runner (`scripts/run_tests.py`)
