# Installation & Run Guide

## Requirements

- Python 3.10+ (recommended)
- macOS / Linux / Windows

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Build the KB index

```bash
python scripts/build_index.py
```

This creates the local index under `.cache/`.

## Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

Open the UI:

- `http://127.0.0.1:8000/`

## Quick verification

Try a few in-scope questions:

- “What are your pricing models?”
- “What is your SLA for a critical outage (Severity 1)?”

And out-of-scope:

- “What is Bitcoin price today?”

