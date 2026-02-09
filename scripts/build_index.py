import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.rag import build_index

if __name__ == "__main__":
    stats = build_index()
    print("Index built:", stats)
