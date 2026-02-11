import json
from pathlib import Path

from app.main import chat, ChatIn

def main():
    cases = json.loads(Path("data/test_cases.json").read_text(encoding="utf-8"))
    ok = 0
    for i, c in enumerate(cases, 1):
        q = c["q"]
        exp = c.get("expect_mode")
        resp = chat(ChatIn(question=q)).body
        data = json.loads(resp.decode("utf-8"))
        mode = data.get("mode", "grounded" if not data.get("is_fallback") else "fallback")
        good = (exp is None) or (mode == exp)
        status = "OK" if good else "MISMATCH"
        print(f"[{status}] {i:02d}. {q}")
        print(f"  mode={mode}  confidence={float(data.get('confidence',0)):.2f}  sources={data.get('sources')}")
        if not good:
            print(f"  expected={exp}")
        ok += 1 if good else 0
    print(f"\nPassed: {ok}/{len(cases)}")

if __name__ == "__main__":
    main()
