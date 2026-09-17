"""One-click local smoke test against the OFFICIAL AML Add/Search contract.

No manual server needed: this script spawns `uvicorn app:app` in the background,
waits for it to be ready (polls /health), runs the assertions, then tears the
server down. Real HTTP, exactly mirroring the platform's Add -> Search flow.

    python smoke_test.py

Asserts response SHAPES only -- no LLM, no Key, no network beyond localhost.
Saves you the 1/hour official smoke quota.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import time

# Ensure the spawned `uvicorn app:app` finds app.py / store.py even when this
# script is launched from the repo root (e.g. `python src/smoke_test.py`).
_HERE = os.path.dirname(os.path.abspath(__file__))
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
PORT = 8000


def _start_server() -> subprocess.Popen:
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--port", str(PORT)],
        cwd=_HERE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BASE + "/health", timeout=2) as r:
                if r.status == 200:
                    return proc
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.3)
    proc.terminate()
    raise RuntimeError("uvicorn did not become ready within 30s")


def post(path: str, payload: dict) -> tuple[dict, int]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE + path, data=data,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode("utf-8")), r.status


def check(cond: bool, msg: str):
    if not cond:
        raise AssertionError("SMOKE FAIL: " + msg)
    print("  ok -", msg)


def main():
    print("starting uvicorn (auto)...")
    server = _start_server()
    try:
        uid = "eval:smoke:locomo:conv-0"
        sid = "eval:smoke:sample:0"
        rid = "eval:smoke:locomo_refined:conv-0:chunk-0"

        # Add
        add_body = {
            "request_id": rid,
            "messages": [
                {"role": "user", "timestamp": 1704067200000, "content": "Rob lives in Sweden."},
                {"role": "assistant", "timestamp": 1704067201000, "content": "Nice."},
            ],
            "user_id": uid,
            "session_id": sid,
        }
        add_resp, status = post("/add", add_body)
        check(status == 200, f"Add returns HTTP 200 (got {status})")
        check(add_resp.get("success") is True, "Add response success == true")
        check(add_resp.get("request_id") == rid, "Add echoes request_id exactly")
        check(add_resp.get("user_id") == uid, "Add echoes user_id exactly")
        check(add_resp.get("session_id") == sid, "Add echoes session_id exactly")

        # Search (expect a hit)
        search_body = {"query": "Where does Rob live?", "user_id": uid, "top_k": 100}
        s_resp, status = post("/search", search_body)
        check(status == 200, f"Search returns HTTP 200 (got {status})")
        check(isinstance(s_resp.get("data"), list), "Search response has top-level `data` array")
        check(len(s_resp["data"]) > 0, "Search returns >=1 hit for known user_id")
        first = s_resp["data"][0]
        check(bool(first.get("id")), "data[].id is non-empty")
        check(bool(first.get("content")), "data[].content is non-empty")

        # Search isolation: a different user_id must NOT leak memories
        other, _ = post("/search",
                        {"query": "Where does Rob live?", "user_id": "eval:smoke:other", "top_k": 100})
        check(other.get("data") == [],
              "Search with unrelated user_id returns empty data[] (no cross-user leak)")

        print("\nALL SMOKE CHECKS PASSED")
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    main()
