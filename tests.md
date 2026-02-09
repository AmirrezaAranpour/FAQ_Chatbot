# Test Cases (PDF-aligned)

## In-scope (12 core questions)
See `data/faq_complete.json` for the reference answers and expected sources.

Expectation:
- `is_fallback = false`
- `sources` not empty
- Answer matches reference key points (phrasing may vary, facts must not)

## Out-of-scope
Expectation:
- `is_fallback = true`
- `sources = []`
- Answer equals `FALLBACK_MESSAGE`

Example out-of-scope questions:
- What is Bitcoin price today?
- Can you give me medical advice?


Fallback message used:
Sorry — I don’t have that information in my FAQ knowledge base. Please rephrase your question or contact support.


Core routing:
- For the 12 core questions, the expected answer should match the corresponding `reference_answer` in `data/faq_complete.json`.
