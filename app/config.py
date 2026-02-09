import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
KB_DIR = BASE_DIR / "knowledge_base"
CACHE_DIR = BASE_DIR / ".cache"

INDEX_PATH = CACHE_DIR / "kb.index.faiss"
META_PATH = CACHE_DIR / "kb.chunks.json"

TOP_K = int(os.getenv("TOP_K", "4"))

# Cosine similarity = inner product on normalized vectors
SIMILARITY_THRESHOLD = float(os.getenv("SIM_THRESHOLD", "0.40"))

# Embedding model (robust for English + multilingual questions)
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# LLM backends (optional)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "")

# Lexical overlap guard (helps filter irrelevant retrieval hits)
LEXICAL_THRESHOLD = float(os.getenv("LEX_THRESHOLD", "0.03"))

# Predictable safe fallback message for out-of-scope / insufficient context
FALLBACK_MESSAGE = "Sorry — I don’t have that information in my FAQ knowledge base. Please rephrase your question or contact support."
