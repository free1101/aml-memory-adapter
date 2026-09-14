# AML Memory Adapter (official-contract skeleton)

Local, Key-free harness for the Agent Memory Leaderboard (记忆之巅). Implements
the two HTTP endpoints the platform fixes (`Add` / `Search`) so you can validate
the contract before spending the 1/hour official smoke quota.

## 0. Install & run
```bash
pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

## 1. Local contract smoke (no LLM, no Key)
```bash
python smoke_test.py
```
Asserts: `Add` echoes `request_id`/`user_id`/`session_id` + `success:true`;
`Search` returns top-level `data[]` with non-empty `id`/`content`; an unrelated
`user_id` returns `[]` (no cross-user leak).

## 2. Add -> Search -> eval_input.jsonl
```bash
python make_eval_jsonl.py
```
Feeds a sample conversation via the official `Add` shape, runs `Search` per
question, writes `eval_input.jsonl` with the fields `pipeline.py` reads
(`question` / `gold_answer` / `speaker_1_name` / `speaker_1_memories` /
`retrieved_context`).

## 3. Retrieval quality (LLM-free second line of defense)
```bash
python retrieval_quality.py
```
Token-recall of the gold answer inside `retrieved_context`. Independent of the
platform `ANSWER`/`JUDGE` models.

## 4. Real end-to-end score (still local, YOUR questions only)
Needs an OpenAI-compatible endpoint. Set env:
```bash
ANSWER_API_BASE / ANSWER_API_KEY / ANSWER_MODEL
JUDGE_API_BASE  / JUDGE_API_KEY  / JUDGE_MODEL
```
Clone the official `data/<bench>/pipeline.py` and run (the CLI `--model` flag is
IGNORED; models come from `api_config` env vars):
```bash
python data/locomo-refined/pipeline.py answer   --input eval_input.jsonl --output answers.jsonl
python data/locomo-refined/pipeline.py evaluate --input eval_input.jsonl --answers answers.jsonl --output judge.jsonl
```
NOTE: this scores YOUR questions, not the private held-out benchmark. The private
benchmark + AML Key are required for a rankable leaderboard score.

## 5. Official leaderboard — Hosted route (needs an AML Key)
Apply for an AML Key (`/evaluation`), deploy `Add`/`Search` to a PUBLIC url (not
localhost), pass the compatibility smoke, then run the full eval (`top_k` fixed at
100). Quota: smoke 1/hr, full 1/3 months. Delete eval data within 30 days.

## 6. Code route submission (no Key, recommended for a first pass)
The Code route only needs a **public GitHub repo + Docker + API wrapper notes**;
the maintainers build and deploy the image and run the smoke — **no Eval Key is
issued**. This repo targets that route.

Endpoints exposed by `app:app` (FastAPI):
- `POST /add` — store one chunk. Body `{request_id, messages[], user_id, session_id}`;
  returns `200 {success:true, request_id, user_id, session_id}` only after the
  writes are durable (synchronous).
- `POST /search` — retrieve. Body `{query, user_id, top_k, options?}`;
  returns `200 {data:[{id, content, score?, created_at?}]}`, best-first, empty `[]`
  when nothing matches. `top_k` defaults to 100.
- `GET /health` — liveness probe.

Auth: **none** (the Code route deploys inside the platform; no public exposure, so
no token is wired in). Data isolation key is `user_id` (`session_id` is org-only).

Build & run locally:
```bash
docker build -t aml-memory-adapter .
docker run -p 8000:8000 aml-memory-adapter
# or without Docker:
pip install -r requirements.txt
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

What to paste into the Evaluation Access Request:
- System name / version: `aml-memory-adapter` (placeholder retriever)
- Repository (public): `<your public GitHub repo URL>`
- Docker build/run: `docker build -t aml-memory-adapter .` then
  `docker run -p 8000:8000 aml-memory-adapter`
- Add URL: `http://<host>:8000/add`  ·  Search URL: `http://<host>:8000/search`
  ·  Health URL: `http://<host>:8000/health`
- Auth: `none`  ·  `top_k`: 100
- Note: retrieval is a keyword+recency placeholder (swap-in point is
  `MemoryStore.search` in `store.py`); good enough to pass the contract smoke.

Compliance: eval data is written to an in-container `memories.jsonl` (ephemeral —
reset on every redeploy). Keep it private, avoid logs, and delete within 30 days.

## Contract notes (verified against api-guide)
- Isolation key is `user_id` (Add == Search). `session_id` is org-only.
- `Search` must return `{"data":[{id, content, score?, created_at?}]}`; the
  platform feeds `data[].content` straight into its fixed `ANSWER_MODEL`.
- `store.search` is the SINGLE swap point for a real retriever
  (embedding + hybrid). Nothing else needs to change.
