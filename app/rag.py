from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import List, Dict, Tuple

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from .config import KB_DIR, INDEX_PATH, META_PATH, TOP_K, SIMILARITY_THRESHOLD, EMBED_MODEL, LEXICAL_THRESHOLD

@dataclass
class Chunk:
    text: str
    source: str

_MODEL: SentenceTransformer | None = None

def _get_model() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer(EMBED_MODEL)
    return _MODEL

def _read_kb_files(kb_dir: Path) -> List[Tuple[str, str]]:
    files = sorted([p for p in kb_dir.glob("*.md") if p.is_file()])
    docs = []
    for p in files:
        # Do NOT index the boundary/scope file (it can pollute retrieval)
        if p.name.lower().startswith("00_"):
            continue
        docs.append((p.name, p.read_text(encoding="utf-8")))
    return docs

def _clean(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def _chunk_text(text: str, max_chars: int = 800, overlap: int = 140) -> List[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: List[str] = []
    buf = ""
    for p in parts:
        if not buf:
            buf = p
        elif len(buf) + 2 + len(p) <= max_chars:
            buf += "\n\n" + p
        else:
            chunks.append(buf)
            tail = buf[-overlap:] if overlap > 0 else ""
            buf = (tail + "\n\n" + p).strip()
    if buf:
        chunks.append(buf)
    return chunks

def build_index() -> Dict[str, int]:
    docs = _read_kb_files(KB_DIR)
    model = _get_model()

    all_chunks: List[Chunk] = []
    for fname, content in docs:
        content = _clean(content)
        for c in _chunk_text(content):
            all_chunks.append(Chunk(text=c, source=fname))

    texts = [c.text for c in all_chunks]
    emb = model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
    emb = np.asarray(emb, dtype="float32")

    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)

    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))

    with META_PATH.open("w", encoding="utf-8") as f:
        json.dump([c.__dict__ for c in all_chunks], f, ensure_ascii=False, indent=2)

    return {"docs": len(docs), "chunks": len(all_chunks), "dim": int(emb.shape[1])}

def _load() -> Tuple[faiss.Index, List[Dict]]:
    if not INDEX_PATH.exists() or not META_PATH.exists():
        build_index()
    index = faiss.read_index(str(INDEX_PATH))
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    return index, meta

_STOPWORDS = set([
    "the","a","an","and","or","to","of","in","on","for","with","is","are","do","does","can","we","you","your","our",
    "what","how","when","where","which","about","from","within","into","this","that","it","as","at","by",
    "و","یا","از","به","در","با","برای","که","این","آن","است","هست","را","می","شود","شما","ما","تا","هم"
])

def _tokenize(s: str) -> List[str]:
    s = s.lower()
    s = re.sub(r"[^0-9a-z\u0600-\u06FF]+", " ", s)
    toks = [t for t in s.split() if t and t not in _STOPWORDS and len(t) > 1]
    return toks

def lexical_overlap_ratio(question: str, text: str) -> float:
    q = set(_tokenize(question))
    if not q:
        return 0.0
    t = set(_tokenize(text))
    inter = q.intersection(t)
    return len(inter) / max(1, len(q))

def retrieve(question: str) -> Tuple[List[Dict], float]:
    index, meta = _load()
    model = _get_model()

    q_emb = model.encode([question], normalize_embeddings=True, show_progress_bar=False)
    q_emb = np.asarray(q_emb, dtype="float32")

    scores, ids = index.search(q_emb, TOP_K)
    scores = scores[0].tolist()
    ids = ids[0].tolist()

    results: List[Dict] = []
    for s, i in zip(scores, ids):
        if i == -1:
            continue
        item = dict(meta[i])
        item["score"] = float(s)
        results.append(item)

    best = float(scores[0]) if scores else 0.0
    return results, best

def should_fallback(question: str, chunks: List[Dict], best_score: float) -> bool:
    q = question.lower().strip()
    # Avoid guessing: if user asks for a full/exact price list (not in KB), fallback.
    if any(p in q for p in ["exact price list", "full price list", "complete price list"]):
        return True
    # Gate 1: similarity threshold
    if best_score < SIMILARITY_THRESHOLD:
        return True
    if not chunks:
        return True

    # Gate 2: lexical overlap guard (use MAX overlap across retrieved chunks)
    overlaps = [lexical_overlap_ratio(question, c.get("text", "")) for c in chunks]
    # Disable lexical gate for non-latin input (e.g., Persian) to avoid false fallbacks
    if _is_latin_text(question) and max(overlaps or [0.0]) < LEXICAL_THRESHOLD:
        return True

    return False

def format_context(chunks: List[Dict], max_chars_total: int = 2400) -> str:
    out = []
    used = 0
    for c in chunks:
        block = f"[SOURCE: {c['source']}]\n{c['text']}\n"
        if used + len(block) > max_chars_total:
            break
        out.append(block)
        used += len(block)
    return "\n---\n".join(out)


def _is_latin_text(s: str) -> bool:
    # crude check: if it contains many a-z letters, treat as latin
    letters = sum(1 for ch in s.lower() if 'a' <= ch <= 'z')
    return letters >= max(3, int(0.2 * max(1, len(s))))

def _keywords(question: str) -> List[str]:
    # simple keyword extraction (no external deps)
    q = re.sub(r"[^a-zA-Z0-9\s]", " ", question.lower())
    toks = [t for t in q.split() if len(t) > 2]
    stop = set(["the","and","for","with","from","that","this","what","your","are","you","does","do","can","is","a","an","to","of","in","on","how","much","work","projects","project","first","after","steps","step","happens","call","tell","exactly","actually","end","provide","reach","times"])
    return [t for t in toks if t not in stop][:8]

def answer_from_chunks(question: str, chunks: List[Dict], max_lines: int = 5) -> Tuple[str, List[str]]:
    """Produce a short, question-focused answer by selecting the most relevant lines/sentences
    from retrieved chunks. This reduces 'section dumping' in the non-LLM path."""
    if not chunks:
        return ""

    kws = _keywords(question)
    # Flatten candidate lines
    candidates = []
    for c in chunks:
        src = c.get("source", "")
        for line in c.get("text","").splitlines():
            ln = line.strip()
            if not ln:
                continue
            low = ln.lower()

            # Filter out section-like lines that tend to look 'weird' when returned as answers.
            # Core FAQs should handle these; extractive answers should prefer content lines.
            if low.startswith(("#", "##", "###")):
                continue
            if re.match(r"^(step\s*\d+\b)", low):
                continue
            if re.match(r"^\d+\)\s", low):
                continue
            if low in {"services", "pricing & payments", "support & sla", "policies", "engagement process"}:
                continue

            candidates.append((ln, src))

    def score(line: str) -> float:
        l = line.lower()
        s = 0.0
        # reward keyword hits
        for k in kws:
            if k in l:
                s += 1.0
        # reward numeric/terms for pricing/SLA questions
        if any(x in question.lower() for x in ["cost","price","€","eur","payment","milestone"]):
            if re.search(r"\d", line):
                s += 0.8
            if "€" in line or "eur" in l:
                s += 1.2
            if "40%" in l or "milestone" in l:
                s += 1.0
        if "sla" in question.lower() or "severity" in question.lower():
            if "severity" in l or "business hour" in l or re.search(r"\d", line):
                s += 1.0
        # Support hours: boost lines that look like business hours / days / time ranges
        if "support" in question.lower() and any(x in question.lower() for x in ["hour","hours","when","time","reach"]):
            if re.search(r"\b(mon|tue|wed|thu|fri|monday|tuesday|wednesday|thursday|friday)\b", l):
                s += 1.2
            if re.search(r"\b\d{1,2}:\d{2}\b", line):
                s += 1.2
            if "business hour" in l:
                s += 0.8
        if "resched" in question.lower():
            if "24" in l or "hour" in l:
                s += 1.0
        # penalize very long lines
        s -= 0.002 * len(line)
        return s

    ranked = sorted(candidates, key=lambda x: score(x[0]), reverse=True)

    picked: List[Tuple[str, str]] = []
    used = set()
    for ln, src in ranked:
        if len(picked) >= max_lines:
            break
        key = ln.lower()
        if key in used:
            continue
        # avoid picking generic section titles
        if key in ["services", "pricing & payments", "support & sla", "policies", "engagement process"]:
            continue
        # ensure at least mildly relevant
        if score(ln) <= 0.2 and kws:
            continue
        picked.append((ln, src))
        used.add(key)

    # fallback: take first few non-empty lines if scoring didn't pick anything
    if not picked:
        for ln, _src in candidates[:max_lines]:
            if ln.lower() not in used:
                picked.append((ln, src))
                used.add(ln.lower())
            if len(picked) >= max_lines:
                break

    used_sources = []
    out_lines = []
    for ln, src in picked:
        out_lines.append(ln)
        if src and src not in used_sources:
            used_sources.append(src)
    return "\n".join(out_lines), used_sources


def rerank_chunks(question: str, chunks: List[Dict]) -> List[Dict]:
    """Lightweight source-aware reranking to improve precision for certain intents."""
    q = question.lower()
    def boost(c: Dict) -> float:
        src = (c.get("source") or "").lower()
        b = 0.0
        if any(k in q for k in ["reschedul", "refund", "privacy", "policy"]):
            if "policies.md" in src:
                b += 2.0
        if any(k in q for k in ["sla", "severity", "support hour", "business hour", "outage"]):
            if "support.md" in src:
                b += 2.0
        if any(k in q for k in ["pricing", "price", "payment", "milestone", "fixed price", "time & materials", "time and materials", "t&m"]):
            if "pricing.md" in src:
                b += 2.0
        if any(k in q for k in ["process", "nda", "sprint", "engagement"]):
            if "process.md" in src:
                b += 1.5
        if any(k in q for k in ["service", "discovery", "mvp"]):
            if "services.md" in src:
                b += 1.5
        return b

    # sort by (boost + similarity) if similarity available; otherwise by boost only
    def key(c: Dict):
        return boost(c) + float(c.get("score", 0.0))

    return sorted(chunks, key=key, reverse=True)
