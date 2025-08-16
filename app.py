from fastapi import FastAPI
from pydantic import BaseModel
import time
import uuid

app = FastAPI(title="OathLink Backend (Docker)")

# ---- In-memory store（先讓它能跑；之後要永久化再接 DB/Volume）----
STORE = {"entries": []}

class MemoryWrite(BaseModel):
    content: str
    tags: list[str] = []

def keyword_hits(q: str, entries: list[dict], top_k: int = 5):
    ql = q.lower()
    hits = []
    for e in entries:
        score = 0
        if ql in e["content"].lower():
            score += 2
        score += sum(1 for t in e.get("tags", []) if ql in t.lower())
        if score:
            hits.append((score, e))
    hits.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in hits[:top_k]]

@app.get("/")
def root():
    return {"ok": True, "msg": "OathLink backend is alive"}

@app.get("/health")
def health():
    return {"ok": True, "ts": time.time()}

@app.post("/memory/write")
def memory_write(payload: MemoryWrite):
    entry = {
        "id": str(uuid.uuid4()),
        "content": payload.content,
        "tags": payload.tags or [],
        "ts": time.time(),
    }
    STORE["entries"].append(entry)
    return {"ok": True, "id": entry["id"]}

@app.get("/memory/search")
def memory_search(q: str, top_k: int = 5):
    hits = keyword_hits(q, STORE.get("entries", []), top_k)
    return {"results": hits}    return {"ok": ok, "ts": time.time()}

@app.post("/memory/write")
def memory_write(payload: MemoryWrite):
    logger.info(f"[WRITE] content={payload.content!r}, tags={payload.tags}")
    mid = add_memory(payload.content, payload.tags or [])
    logger.info(f"[WRITE-OK] id={mid}")
    return {"ok": True, "id": mid}

@app.get("/memory/search")
def memory_search(q: str = Query(..., min_length=1), top_k: int = 5):
    logger.info(f"[SEARCH] q={q!r}, top_k={top_k}")
    hits = search_memory(q, top_k)
    logger.info(f"[SEARCH-OK] hits={len(hits)}")
    return {"results": hits}
