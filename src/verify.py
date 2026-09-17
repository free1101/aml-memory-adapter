"""One-shot local verification WITHOUT a live server.

Uses FastAPI's TestClient to call the Add/Search endpoints in-process, so no
uvicorn / port is needed. Mirrors what smoke_test.py + make_eval_jsonl.py +
retrieval_quality.py do against a running server.

    python verify.py
"""
from __future__ import annotations
import json
import os
import sys
import time

# Make sibling modules (app, retrieval_quality) importable no matter which
# directory the script is launched from.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Clean rerun: drop any persisted state so results are deterministic.
for _f in ("memories.jsonl", "eval_input.jsonl"):
    try:
        os.remove(_f)
    except FileNotFoundError:
        pass

from fastapi.testclient import TestClient
from app import app
import retrieval_quality

def main():
    client = TestClient(app)

    # ---------- 1. SMOKE: Add/Search official contract ----------
    uid = "eval:smoke:locomo:conv-0"
    sid = "eval:smoke:sample:0"
    rid = "eval:smoke:locomo_refined:conv-0:chunk-0"

    add_resp = client.post("/add", json={
        "request_id": rid,
        "messages": [
            {"role": "user", "timestamp": 1704067200000, "content": "Rob lives in Sweden."},
            {"role": "assistant", "timestamp": 1704067201000, "content": "Nice."},
        ],
        "user_id": uid,
        "session_id": sid,
    })
    assert add_resp.status_code == 200, add_resp.status_code
    a = add_resp.json()
    assert a["success"] is True
    assert a["request_id"] == rid and a["user_id"] == uid and a["session_id"] == sid

    s_resp = client.post("/search",
                         json={"query": "Where does Rob live?", "user_id": uid, "top_k": 100})
    assert s_resp.status_code == 200
    d = s_resp.json()
    assert isinstance(d["data"], list) and len(d["data"]) > 0
    assert d["data"][0]["id"] and d["data"][0]["content"]

    other = client.post("/search",
                        json={"query": "Where does Rob live?", "user_id": "eval:smoke:other", "top_k": 100}).json()
    assert other["data"] == [], "cross-user leak detected!"
    print("ALL SMOKE CHECKS PASSED (via TestClient)")

    # ---------- 2. MAKE_EVAL flow (same as make_eval_jsonl.py) ----------
    USER_ID = "eval:local:locomo:conv-0"
    SESSION_ID = "eval:local:sample:0"
    TOP_K = 5
    CONVERSATION = [
        ("speaker_1", "I'm Rob. I live in Sweden and I hate sweet coffee."),
        ("speaker_2", "Nice. What do you do for work?"),
        ("speaker_1", "I'm a marine biologist. Last month I went to Lisbon for a conference."),
        ("speaker_2", "Cool. Any plans next month?"),
        ("speaker_1", "Yes, in July 2019 I started a new project on kelp forests."),
    ]
    QUESTIONS = [
        {"id": "q1", "question": "What country does Rob live in?",
         "gold_answer": "Sweden", "speaker_1_name": "Rob"},
        {"id": "q2", "question": "What is Rob's job?",
         "gold_answer": "marine biologist", "speaker_1_name": "Rob"},
        {"id": "q3", "question": "Does Rob like sweet coffee?",
         "gold_answer": "No", "speaker_1_name": "Rob"},
    ]
    base = int(time.time() * 1000)
    for i, (who, text) in enumerate(CONVERSATION):
        role = "user" if who == "speaker_1" else "assistant"
        client.post("/add", json={
            "request_id": f"eval:local:locomo_refined:conv-0:chunk-{i}",
            "messages": [{"role": role, "timestamp": base + i, "content": text}],
            "user_id": USER_ID, "session_id": SESSION_ID,
        })
    rows = []
    for q in QUESTIONS:
        res = client.post("/search",
                          json={"query": q["question"], "user_id": USER_ID, "top_k": TOP_K}).json()
        ctx = "\n".join(f"[{h['id']}] {h['content']}" for h in res["data"])
        rows.append({
            "id": q["id"],
            "question": q["question"],
            "gold_answer": q["gold_answer"],
            "speaker_1_name": q["speaker_1_name"],
            "speaker_1_memories": ctx,
            "retrieved_context": ctx,
        })
    with open("eval_input.jsonl", "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} rows -> eval_input.jsonl")

    # ---------- 3. RETRIEVAL QUALITY (LLM-free) ----------
    print("=== RETRIEVAL_QUALITY ===")
    retrieval_quality.main("eval_input.jsonl")

if __name__ == "__main__":
    main()
