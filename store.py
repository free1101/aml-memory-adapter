"""Memory store + retriever for the AML Add/Search adapter.

Contract-aligned with agentmemoryleaderboard.ai/api-guide:
  - isolation key is `user_id` (Add and Search must agree)
  - `created_at` is stored as Unix milliseconds (official `timestamp` is ms)
  - `search` returns scored hits; the placeholder keyword + recency ranker is
    the SINGLE swap point for your real `knowledge_service` (embedding +
    hybrid retrieval). Everything else (app.py, the eval scripts) stays put.
"""
from __future__ import annotations
import json
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

TOKEN_RE = re.compile(r"[a-zA-Z0-9\u4e00-\u9fff]+")

# A timestamp below this value is treated as seconds (old data) and normalized
# to milliseconds; values at/above are already milliseconds. ~year 2001 in ms.
_SECONDS_THRESHOLD = 1_000_000_000_000

def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())

def _to_ms(value) -> float:
    """Normalize a timestamp that may be seconds (old data) or ms (new) to ms."""
    if value is None:
        return time.time() * 1000.0
    if isinstance(value, (int, float)) and value < _SECONDS_THRESHOLD:
        return float(value) * 1000.0
    return float(value)

@dataclass
class MemoryEntry:
    id: str
    user_id: str = "global"       # isolation key shared by Add and Search
    session_id: str = ""          # source session (organization only, not filtered)
    role: str = "user"            # "user" | "assistant"
    type: str = "conversation"    # internal tag: conversation | event | document | fact
    content: str = ""
    created_at: float = field(default_factory=lambda: time.time() * 1000.0)  # ms
    metadata: dict = field(default_factory=dict)

    def to_record(self) -> dict:
        return asdict(self)

    def created_at_iso(self) -> str:
        # Spec sample is "2026-07-01T12:00:00Z"; emit RFC3339 UTC with `Z`.
        dt = datetime.fromtimestamp(self.created_at / 1000.0, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

class MemoryStore:
    def __init__(self, persist_path: str | Path | None = None):
        self.persist_path = Path(persist_path) if persist_path else None
        self._entries: list[MemoryEntry] = []
        self._seq = 0
        if self.persist_path and self.persist_path.exists():
            self._load()

    def add(self, content: str, user_id: str, session_id: str,
            role: str = "user", type: str = "conversation",
            entry_id: str | None = None, created_at_ms: int | None = None,
            metadata: dict | None = None) -> str:
        self._seq += 1
        eid = entry_id or f"mem_{self._seq:06d}"
        entry = MemoryEntry(
            id=eid, user_id=user_id, session_id=session_id, role=role,
            type=type, content=content,
            created_at=_to_ms(created_at_ms),
            metadata=metadata or {},
        )
        self._entries.append(entry)
        self._save()
        return eid

    def search(self, query: str, user_id: str | None = None,
               top_k: int = 100, recency_weight: float = 0.05
               ) -> list[tuple[float, MemoryEntry]]:
        """Return up to `top_k` (score, entry) pairs for `user_id`, best first.

        Placeholder ranker: token overlap (keyword) + recency decay. This is the
        ONLY function to replace when wiring in a real retriever.
        """
        q_tokens = tokenize(query)
        q_set = set(q_tokens)
        scored: list[tuple[float, MemoryEntry]] = []
        now_ms = time.time() * 1000.0
        for e in self._entries:
            if user_id is not None and e.user_id != user_id:
                continue
            e_tokens = tokenize(e.content)
            if q_tokens:
                overlap = len(q_set & set(e_tokens))
                density = overlap / max(1, len(e_tokens))
                keyword_score = overlap + density
            else:
                keyword_score = 0.0
            age_days = max(0.0, now_ms - e.created_at) / 86_400_000.0
            recency_score = recency_weight * (1.0 / (1.0 + age_days))
            scored.append((keyword_score + recency_score, e))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]

    def _save(self):
        if not self.persist_path:
            return
        tmp = self.persist_path.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            for e in self._entries:
                f.write(json.dumps(e.to_record(), ensure_ascii=False) + "\n")
        tmp.replace(self.persist_path)

    def _load(self):
        with self.persist_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                # Backward-compat: old files used `scope` and seconds timestamps.
                if "scope" in d and "user_id" not in d:
                    d["user_id"] = d.pop("scope")
                d["created_at"] = _to_ms(d.get("created_at"))
                d.setdefault("user_id", "global")
                d.setdefault("session_id", "")
                d.setdefault("role", "user")
                d.setdefault("type", "conversation")
                d.setdefault("content", "")
                d.setdefault("metadata", {})
                self._entries.append(MemoryEntry(**d))
        self._seq = len(self._entries)
