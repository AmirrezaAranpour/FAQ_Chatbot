from __future__ import annotations
import os

from .config import OPENAI_MODEL, OLLAMA_MODEL, FALLBACK_MESSAGE

SYSTEM_PROMPT_V1 = """You are an FAQ assistant for ARV Digital Services.
Answer the user's question using the provided CONTEXT.
If the CONTEXT does not contain the answer, say you don't have enough information.
Be concise and helpful.
Language: English.
"""

SYSTEM_PROMPT_V2 = """You are an FAQ assistant for ARV Digital Services.
You MUST answer using ONLY the information in the provided CONTEXT.
If the CONTEXT does not contain enough information, say you do not have enough information in the knowledge base and suggest contacting support.
Do NOT guess. Do NOT add anything beyond the CONTEXT.
Language: English.
Tone: professional and friendly.
Keep the answer short and actionable (max 6 sentences).
At the end, add a line: 'Sources: <comma-separated filenames>' using the sources present in CONTEXT.
"""

# Active prompt used by the chatbot (submission version)
SYSTEM_PROMPT = SYSTEM_PROMPT_V2

TEMPERATURE = 0.0

def _openai_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))

def _ollama_available() -> bool:
    return bool(OLLAMA_MODEL)

def _extract_sources(context: str) -> list[str]:
    srcs = []
    for line in context.splitlines():
        if line.startswith("[SOURCE:"):
            s = line.replace("[SOURCE:", "").replace("]", "").strip()
            if s and s not in srcs:
                srcs.append(s)
    return srcs

def _extractive_answer(context: str) -> str:
    lines = [ln.strip() for ln in context.splitlines() if ln.strip()]
    lines = [ln for ln in lines if not ln.startswith("[SOURCE:")]
    return "\n".join(lines[:8]).strip()

def generate_answer(question: str, context: str, sources: list[str] | None = None) -> str:
    if _openai_available():
        try:
            from openai import OpenAI
            client = OpenAI()
            try:
                resp = client.responses.create(
                    model=OPENAI_MODEL,
                    input=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"QUESTION: {question}\n\nCONTEXT:\n{context}"},
                    ],
                    temperature=0,
                )
                txt = getattr(resp, "output_text", None)
                if txt:
                    return txt.strip()
            except Exception:
                pass

            chat = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"QUESTION: {question}\n\nCONTEXT:\n{context}"},
                ],
                temperature=0,
            )
            return chat.choices[0].message.content.strip()
        except Exception:
            pass

    if _ollama_available():
        try:
            import ollama
            r = ollama.chat(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"QUESTION: {question}\n\nCONTEXT:\n{context}"},
                ],
                options={"temperature": 0},
            )
            return r["message"]["content"].strip()
        except Exception:
            pass
    # No LLM provider configured -> return empty so the backend can use extractive answer logic.
    return ""
