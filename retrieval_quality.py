"""LLM-free retrieval quality metric (second line of defense).

Reads eval_input.jsonl (produced by make_eval_jsonl.py) and measures how much
of the gold answer's tokens appear in the retrieved context. This evaluates
SEARCH quality independently of the platform's fixed ANSWER/JUDGE models.

    python retrieval_quality.py [path/to/eval_input.jsonl]

Metric: token recall = |gold_tokens ∩ retrieved_tokens| / |gold_tokens|
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

TOKEN_RE = re.compile(r"[a-zA-Z0-9\u4e00-\u9fff]+")

def tokenize(text: str) -> set[str]:
    return set(TOKEN_RE.findall((text or "").lower()))

def recall(gold: str, retrieved: str) -> float:
    g = tokenize(gold)
    if not g:
        return 0.0
    r = tokenize(retrieved)
    if not r:
        return 0.0
    return len(g & r) / len(g)

def main(path: str = "eval_input.jsonl"):
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"not found: {p}")
    rows = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise SystemExit(f"empty: {p}")
    total = 0.0
    print(f"{'id':<6} {'recall':>7}  question")
    for row in rows:
        gold = row.get("gold_answer", "")
        ctx = row.get("retrieved_context") or row.get("speaker_1_memories") or ""
        score = recall(gold, ctx)
        total += score
        print(f"{row.get('id', ''):<6} {score:>7.3f}  {row.get('question', '')}")
    print(f"\nmean retrieval recall: {total / len(rows):.3f}  (n={len(rows)})")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "eval_input.jsonl")
