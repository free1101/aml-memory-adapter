"""Local demo: feed memories via the OFFICIAL Add contract, run Search per
query, emit eval_input.jsonl consumable by AML's data/<bench>/pipeline.py.

No LLM is called here. Real scores need ANSWER_API_BASE / ANSWER_API_KEY /
ANSWER_MODEL + JUDGE_* env vars and the official pipeline.py (see README).

Run the server first (python -m uvicorn app:app --port 8000), then:
    python make_eval_jsonl.py
"""
from __future__ import annotations
import json
import time
import urllib.request

BASE = "http://127.0.0.1:8000"
PIPELINE_INPUT = "eval_input.jsonl"
USER_ID = "eval:local:locomo:conv-0"
SESSION_ID = "eval:local:sample:0"
TOP_K = 5  # official eval fixes top_k=100; local demo keeps it small

# (speaker, text) -> speaker_1 becomes role "user", speaker_2 role "assistant"
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

def role_of(speaker: str) -> str:
    return "user" if speaker == "speaker_1" else "assistant"

def post(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE + path, data=data,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode("utf-8"))

def main():
    base = int(time.time() * 1000)
    for i, (who, text) in enumerate(CONVERSATION):
        post("/add", {
            "request_id": f"eval:local:locomo_refined:conv-0:chunk-{i}",
            "messages": [{"role": role_of(who), "timestamp": base + i, "content": text}],
            "user_id": USER_ID,
            "session_id": SESSION_ID,
        })
    rows = []
    for q in QUESTIONS:
        res = post("/search", {"query": q["question"], "user_id": USER_ID, "top_k": TOP_K})
        ctx = "\n".join(f"[{h['id']}] {h['content']}" for h in res["data"])
        rows.append({
            "id": q["id"],
            "question": q["question"],
            "gold_answer": q["gold_answer"],
            "speaker_1_name": q["speaker_1_name"],
            "speaker_1_memories": ctx,
            "retrieved_context": ctx,
        })
    with open(PIPELINE_INPUT, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} rows -> {PIPELINE_INPUT}")

if __name__ == "__main__":
    main()
