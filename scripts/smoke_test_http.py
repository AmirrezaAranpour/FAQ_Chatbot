import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

def post(url: str, payload: dict) -> dict:
    req = Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type":"application/json"})
    with urlopen(req) as r:
        return json.loads(r.read().decode("utf-8"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8001)
    args = ap.parse_args()

    url = f"http://127.0.0.1:{args.port}/chat"
    cases = json.loads(Path("data/test_cases.json").read_text(encoding="utf-8"))

    ok = 0
    for i, c in enumerate(cases, 1):
        q = c["q"]
        exp = c.get("expect_mode")
        data = post(url, {"question": q})
        mode = data.get("mode", "grounded" if not data.get("is_fallback") else "fallback")
        good = (exp is None) or (mode == exp)
        status = "OK" if good else "MISMATCH"
        print(f"[{status}] {i:02d}. {q}")
        print(f"  mode={mode}  confidence={float(data.get('confidence',0)):.2f}  sources={data.get('sources')}")
        ok += 1 if good else 0

    print(f"\nPassed: {ok}/{len(cases)}")

if __name__ == "__main__":
    main()
