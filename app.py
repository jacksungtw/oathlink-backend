from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import time

from storage import add_memory, search_memory, health as db_health

app = FastAPI()

class MemoryWrite(BaseModel):
    content: str
    tags: Optional[List[str]] = None

@app.get("/health")
def health():
    return {"ok": True, "ts": time.time(), "db": db_health()}

@app.post("/memory/write")
def memory_write(payload: MemoryWrite):
    mid = add_memory(payload.content, payload.tags or [])
    return {"ok": True, "id": mid}

@app.get("/memory/search")
def memory_search(q: str, top_k: int = 5):
    hits = search_memory(q, top_k)
    return {"results": hits}
