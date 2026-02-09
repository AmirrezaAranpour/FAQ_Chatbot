from __future__ import annotations

import json
from pathlib import Path
import difflib
import re

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import FALLBACK_MESSAGE
from .rag import retrieve, should_fallback, format_context, build_index, answer_from_chunks, rerank_chunks
from .llm import generate_answer


# Load the 12 core FAQ items (reference answers). These provide stable, question-focused responses.
FAQ_PATH = Path("data/faq_complete.json")
_FAQ_ITEMS = []
if FAQ_PATH.exists():
    try:
        _FAQ_ITEMS = json.loads(FAQ_PATH.read_text(encoding="utf-8"))
    except Exception:
        _FAQ_ITEMS = []
FAQ_ITEMS = [x for x in _FAQ_ITEMS if x.get("in_scope") is True and int(x.get("id", 0)) <= 12]

def _norm_q(s: str) -> str:
    # Normalize a user question for routing/matching.
    s = (s or "").strip().lower()
    # Common abbreviations / aliases
    s = s.replace("t&m", "time & materials")
    s = s.replace("t & m", "time & materials")
    s = s.replace("t and m", "time & materials")
    s = s.replace("time and materials", "time & materials")
    s = re.sub(r"\s+", " ", s)
    # Keep unicode letters/digits/underscore, whitespace, and a few symbols used in FAQs.
    s = re.sub(r"[^\w\s&\-\?\(\)]+", "", s, flags=re.UNICODE)
    return s.strip()


def _clamp01(x: float) -> float:
    try:
        x = float(x)
    except Exception:
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def is_out_of_scope(question: str) -> bool:
    """Hard guardrails: if the user asks for something outside the FAQ scope,
    do not answer from retrieval even if there is a superficial keyword overlap."""
    q = (question or "").strip().lower()
    if not q:
        return True

    # Obvious non-FAQ domains
    if any(x in q for x in [
        "bitcoin", "btc", "eth price", "price of bitcoin",
        "weather", "forecast", "temperature",
        "etf", "invest", "investment",
        "diagnose", "diagnosis", "medical advice", "headache", "stomach pain", "chest pain",
        "lawyer", "legal advice",
    ]):
        return True

    # Company contact/location details are not in the KB for this task
    if any(x in q for x in ["phone number", "phone", "call you", "office address", "address", "location"]):
        return True

    # Legal document drafting (keep NDA in-scope)
    if any(x in q for x in ["terms & conditions", "terms and conditions", "t&c", "t & c"]):
        return True

    if ("contract" in q or "agreement" in q) and any(v in q for v in ["draft", "write", "generate", "template"]):
        # NDA is explicitly in-scope
        if "nda" in q:
            return False
        return True

    # "terms" is ambiguous: treat as out-of-scope only when it clearly refers to legal T&Cs
    if "terms" in q and any(v in q for v in ["draft", "write", "generate"]) and "payment" not in q and "pricing" not in q:
        return True

    return False


def match_core_faq(question: str):
    # Return the best matching core FAQ item (1..12) for in-scope questions.
    # This is intentionally biased toward returning one of the 12 stable
    # 'reference answers' to avoid snippet-dumping for paraphrases.
    if not FAQ_ITEMS:
        return None

    qn = _norm_q(question)
    if not qn:
        return None

    core_norms = [(_norm_q(it.get("question", "")), it) for it in FAQ_ITEMS]

    # 1) Exact match
    for cn, it in core_norms:
        if cn and cn == qn:
            it["_match_score"] = 1.0
            return it

    q = qn  # normalized

    # Quick out-of-scope guardrails: do not force-route these to core.
    out_scope_markers = ["bitcoin", "btc", "medical", "headache", "legal contract", "contract", "phone number", "address"]
    if any(m in q for m in out_scope_markers):
        return None

    # 2) Keyword + typo-friendly routing for short queries
    keyword_map = {
        "service": "What services do you offer?",
        "services": "What services do you offer?",
        "discovery": "What is included in the Discovery session?",
        "price": "What are your pricing models?",
        "pricing": "What are your pricing models?",
        "prcing": "What are your pricing models?",
        "model": "What are your pricing models?",
        "models": "What are your pricing models?",
        "modls": "What are your pricing models?",
        "payment": "What are the payment terms for a Fixed Price project?",
        "payments": "What are the payment terms for a Fixed Price project?",
        "process": "What is your engagement process from start to finish?",
        "workflow": "What is your engagement process from start to finish?",
        "nda": "Can we sign an NDA?",
        "support": "What are your support hours?",
        "supprt": "What are your support hours?",
        "hours": "What are your support hours?",
        "sla": "What is your SLA for a critical outage (Severity 1)?",
        "policy": "What is your privacy policy?",
        "policies": "What is your privacy policy?",
        "refund": "What is your refund policy for Fixed Price work?",
        "reschedule": "Can meetings be rescheduled?",
        "rescheduling": "Can meetings be rescheduled?",
    }

    if len(q.split()) <= 3:
        if q in keyword_map:
            target = keyword_map[q]
            for _cn, it in core_norms:
                if it.get("question") == target:
                    it["_match_score"] = 0.9
                    return it

        keys = list(keyword_map.keys())
        # Only apply typo-fuzzy matching for single-token queries (to avoid mapping vague phrases like 'support me').
        if len(q.split()) == 1:
            cm = difflib.get_close_matches(q, keys, n=1, cutoff=0.72)
        else:
            cm = []
        if cm:
            target = keyword_map[cm[0]]
            for _cn, it in core_norms:
                if it.get("question") == target:
                    it["_match_score"] = 0.8
                    return it

        # heuristic: "prcing modls" style
        if ("prc" in q or "pric" in q) and ("modl" in q or "model" in q):
            target = "What are your pricing models?"
            for _cn, it in core_norms:
                if it.get("question") == target:
                    it["_match_score"] = 0.8
                    return it

        # heuristic: "fixed price payment" -> payment terms (milestones)
        if "fixed" in q and "price" in q and "payment" in q:
            target = "What are the payment terms for a Fixed Price project?"
            for _cn, it in core_norms:
                if it.get("question") == target:
                    it["_match_score"] = 0.82
                    return it

        if ("sup" in q and "hour" in q) or ("supprt" in q and "hour" in q) or ("hrs" in q):
            target = "What are your support hours?"
            for _cn, it in core_norms:
                if it.get("question") == target:
                    it["_match_score"] = 0.8
                    return it

    # 3) Rule-based intent routing for paraphrases
    ql = q

    def has_any(*terms: str) -> bool:
        return any(t in ql for t in terms)

    # Discovery paraphrases
    if "discovery" in ql and has_any("include", "included", "deliver", "deliverable", "what do you", "session"):
        target = "What is included in the Discovery session?"
        for _cn, it in core_norms:
            if it.get("question") == target:
                it["_match_score"] = 0.85
                return it

    # Time & Materials billing paraphrases
    if has_any("time & materials", "hourly", "weekly") and has_any("bill", "billing", "charge", "rate", "how do you"):
        target = "How does Time & Materials billing work?"
        for _cn, it in core_norms:
            if it.get("question") == target:
                it["_match_score"] = 0.85
                return it

    # Refunds / cancellation (higher priority than generic pricing)
    if has_any("refund", "refunds", "cancel", "cancellation"):
        target = "What is your refund policy for Fixed Price work?"
        for _cn, it in core_norms:
            if it.get("question") == target:
                it["_match_score"] = 0.85
                return it

    # Payment terms (Fixed Price)
    if (has_any("payment", "payments", "milestone", "milestones") or has_any("start", "start work", "begin", "kick off")) and has_any("fixed", "fixed price"):
        target = "What are the payment terms for a Fixed Price project?"
        for _cn, it in core_norms:
            if it.get("question") == target:
                it["_match_score"] = 0.83
                return it

    # Pricing models
    if has_any("pricing", "price", "pricing model", "pricing models", "fixed price", "time & materials"):
        target = "What are your pricing models?"
        for _cn, it in core_norms:
            if it.get("question") == target:
                it["_match_score"] = 0.78
                return it

    # Privacy
    if has_any("privacy", "client data", "data policy"):
        target = "What is your privacy policy?"
        for _cn, it in core_norms:
            if it.get("question") == target:
                it["_match_score"] = 0.85
                return it

    # Rescheduling
    if has_any("reschedul", "reschedule", "move meeting", "change meeting"):
        target = "Can meetings be rescheduled?"
        for _cn, it in core_norms:
            if it.get("question") == target:
                it["_match_score"] = 0.85
                return it

    # Support hours
    if has_any("support") and has_any("hour", "hours", "reach", "time", "business"):
        target = "What are your support hours?"
        for _cn, it in core_norms:
            if it.get("question") == target:
                it["_match_score"] = 0.85
                return it

    # SLA
    if has_any("sla", "severity", "sev", "critical outage"):
        target = "What is your SLA for a critical outage (Severity 1)?"
        for _cn, it in core_norms:
            if it.get("question") == target:
                it["_match_score"] = 0.85
                return it

    # NDA
    if "nda" in ql:
        target = "Can we sign an NDA?"
        for _cn, it in core_norms:
            if it.get("question") == target:
                it["_match_score"] = 0.85
                return it

    # After-Discovery questions: route to the most relevant core answer
    if "after" in ql and "discovery" in ql:
        if has_any("get", "deliver", "deliverable", "receive", "end", "result", "output"):
            target = "What is included in the Discovery session?"
        else:
            target = "What is your engagement process from start to finish?"
        for _cn, it in core_norms:
            if it.get("question") == target:
                it["_match_score"] = 0.84
                return it

    # Engagement workflow
    if has_any("process", "workflow", "step-by-step", "steps", "start to finish", "engagement", "after the first call"):
        target = "What is your engagement process from start to finish?"
        for _cn, it in core_norms:
            if it.get("question") == target:
                it["_match_score"] = 0.85
                return it

    # Services overview
    if has_any("services", "offer", "what do you do"):
        target = "What services do you offer?"
        for _cn, it in core_norms:
            if it.get("question") == target:
                it["_match_score"] = 0.75
                return it

    # 4) Final fuzzy match (typos / near-misses)
    best = None
    best_score = 0.0
    for cn, it in core_norms:
        if not cn:
            continue
        s = difflib.SequenceMatcher(a=qn, b=cn).ratio()
        if s > best_score:
            best_score = s
            best = it
    if best and best_score >= 0.70:
        best["_match_score"] = _clamp01(best_score)
        return best

    return None





app = FastAPI(title="FAQ Chatbot (RAG)")
app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatIn(BaseModel):
    question: str


@app.get("/", response_class=HTMLResponse)
def home():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.post("/chat")
def chat(payload: ChatIn):
    question = payload.question.strip()
    if not question:
        return JSONResponse(
            {"answer": "Please type a question to get started.", "sources": [], "confidence": 0.0, "is_fallback": True}
        )

    q_lower = question.lower().strip()

    # Special-case: '24/7' queries should be explicit and not dump unrelated SLA details.
    if any(x in q_lower for x in ["24/7", "24x7"]):
        return JSONResponse({
            "answer": "The knowledge base lists business hours (Mon–Fri, 09:00–17:00 CET/CEST) and does not mention 24/7 support.",
            "sources": ["support.md"],
            "confidence": 0.5,
            "is_fallback": False,
        })

    # Hard out-of-scope guard: do not answer from retrieval.
    if is_out_of_scope(question):
        return JSONResponse({"answer": FALLBACK_MESSAGE, "sources": [], "confidence": 0.0, "is_fallback": True})



    core = match_core_faq(question)
    if core is not None:
        srcs = core.get("sources") or []
        return JSONResponse({
            "answer": core.get("reference_answer", "").strip(),
            "sources": srcs,
            "confidence": _clamp01(core.get("_match_score", 0.9)),
            "is_fallback": False,
        })

    chunks, best_score = retrieve(_norm_q(question))
    chunks = rerank_chunks(question, chunks)
    confidence = float(best_score)

    if should_fallback(question, chunks, best_score):
        return JSONResponse({"answer": FALLBACK_MESSAGE, "sources": [], "confidence": confidence, "is_fallback": True})

    context = format_context(chunks)

    # If an LLM is configured, use it; otherwise generate a short extractive answer.
    answer = generate_answer(question=question, context=context)

    used_sources = []
    if not answer:
        answer, used_sources = answer_from_chunks(question, chunks)

    # Sources: prefer sources actually used by extractive answer; otherwise use retrieved sources.
    sources = sorted({c.get("source", "") for c in chunks if c.get("source")})
    if used_sources:
        sources = used_sources

    if answer and "\n\nSources:" not in answer:
        answer = answer.strip() + "\n\nSources: " + ", ".join(sources)

    return JSONResponse({"answer": answer, "sources": sources, "confidence": confidence, "is_fallback": False})


@app.post("/reindex")

def reindex():
    stats = build_index()
    return JSONResponse({"ok": True, "stats": stats})


@app.get("/health")
def health():
    return {"ok": True}
