import os
import time
import uuid
from typing import List, Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel

app = FastAPI(title="OathLink Backend (MVP)")

# ---- Models ----
class MemoryWrite(BaseModel):
    content: str
    tags: Optional[List[str]] = None

# ---- In-memory store (可先用記憶體，之後再換成 DB/Volume) ----
STORE = {"entries": []}

# ---- Utilities ----
def keyword_hits(q: str, entries: List[dict], top_k: int = 5):
    if not q:
        return entries[:top_k]
    terms = [t for t in q.lower().split() if t]
    scored = []
    for e in entries:
        text = f"{e.get('content','')} {' '.join(e.get('tags', []))}".lower()
        score = sum(text.count(t) for t in terms)
        if score > 0:
            scored.append((score, e))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored[:top_k]]

# ---- Routes ----
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
def memory_search(q: str = Query("", description="keyword query"), top_k: int = 5):
    hits = keyword_hits(q, STORE.get("entries", []), top_k=top_k)
    return {"results": hits}

# ---- Uvicorn entry (本地測試用；Railway 仍由 start command 啟動) ----
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("app:app", host="0.0.0.0", port=port)