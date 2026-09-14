"""FastAPI adapter exposing AML-style Add / Search endpoints.

Contract-aligned with agentmemoryleaderboard.ai/api-guide (verified):
  Add  : POST {request_id, messages[], user_id, session_id}
         -> 200 {success:true, request_id, user_id, session_id} (echoed exactly)
  Search: POST {query, user_id, top_k, options?}
         -> 200 {data:[{id, content, score?, created_at?}]}
`user_id` is the sole isolation key; `data` must be a top-level array.
The fixed platform ANSWER/JUDGE models read `data[].content` directly, so
whatever your `Search` returns is what gets scored.
"""
from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel
from store import MemoryStore

store = MemoryStore(persist_path="memories.jsonl")
app = FastAPI(title="AML Memory Adapter")

class AddMessage(BaseModel):
    role: str                       # "user" | "assistant"
    content: str
    timestamp: int | None = None    # Unix milliseconds

class AddRequest(BaseModel):
    request_id: str
    messages: list[AddMessage]
    user_id: str
    session_id: str

class SearchRequest(BaseModel):
    query: str
    user_id: str
    top_k: int = 100                # official eval fixes this at 100
    options: list[str] | None = None

class MemoryHit(BaseModel):
    id: str
    content: str
    score: float | None = None
    created_at: str | None = None   # ISO 8601

class AddResponse(BaseModel):
    success: bool
    request_id: str
    user_id: str
    session_id: str

class SearchResponse(BaseModel):
    data: list[MemoryHit]           # empty results -> []

@app.get("/health")
def health():
    return {"status": "ok", "entries": len(store._entries)}

@app.post("/add", response_model=AddResponse)
def add(req: AddRequest):
    for m in req.messages:
        store.add(
            content=m.content,
            user_id=req.user_id,
            session_id=req.session_id,
            role=m.role,
            created_at_ms=m.timestamp,
        )
    return AddResponse(
        success=True,
        request_id=req.request_id,
        user_id=req.user_id,
        session_id=req.session_id,
    )

@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    hits = store.search(req.query, user_id=req.user_id, top_k=req.top_k)
    data = [
        MemoryHit(
            id=e.id,
            content=e.content,
            score=round(s, 4),
            created_at=e.created_at_iso(),
        )
        for s, e in hits
    ]
    return SearchResponse(data=data)
