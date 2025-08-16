# 置頂：匯入 + Token 驗證
import os, time
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from storage import search_memory, add_memory

AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")
app = FastAPI(title="OathLink Backend")

def _check(token: str | None):
    if not AUTH_TOKEN:
        return
    if token != AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
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
def memory_write(payload: ComposeReq, x_auth_token: str | None = Header(default=None)):
    _check(x_auth_token)
    mid = add_memory(payload.input, payload.tags or [])
    return {"ok": True, "id": mid}

@app.get("/memory/search")
def memory_search(q: str, top_k: int = 5, x_auth_token: str | None = Header(default=None)):
    _check(x_auth_token)
    return {"results": search_memory(q, top_k)}
# 新增：/compose（人格 + 記憶注入，回傳 prompt）
PERSONA = "【人格模板】稱呼使用師父/您/願主；先結論後理由；禁止廢話與不敬語。"

class ComposeReq(BaseModel):
    input: str
    tags: Optional[List[str]] = None
    top_k: int = 5

@app.post("/compose")
def compose(req: ComposeReq, x_auth_token: str | None = Header(default=None)):
    _check(x_auth_token)
    hits = search_memory(req.input, req.top_k)
    ctx = "\n".join([f"- {h['content']}" for h in hits]) or "- (無)"
    prompt = f"""{PERSONA}

【相關記憶】
{ctx}

【當前輸入】
{req.input}

【請以人格口吻輸出】"""
    return {"prompt": prompt, "mem_hits": hits}