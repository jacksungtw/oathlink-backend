# app.py — OathLink Backend (with /compose1 and /compose2 for test)
import os, time, uuid, sqlite3
from typing import List, Optional, Any, Dict
from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel

# ---------- Config ----------
DB_PATH = os.getenv("DB_PATH", "/app/data/memory.db")
AUTH_TOKEN_ENV = os.getenv("AUTH_TOKEN")  # 若設定就啟用驗證
PERSONA_PROMPT = (
    "你是 OathLink 的『穩定語風人格助手』。"
    "回覆語氣一致、條列清晰，會在必要時補上步驟與指令。"
)

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ---------- DB helpers ----------
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            tags TEXT,
            ts REAL NOT NULL
        )
    """)
    return con

def write_memory(content: str, tags: Optional[List[str]]) -> str:
    mid = str(uuid.uuid4())
    with _conn() as con:
        con.execute(
            "INSERT INTO memories (id, content, tags, ts) VALUES (?,?,?,?)",
            (mid, content, ",".join(tags or []), time.time()),
        )
    return mid

def search_memory(q: str, top_k: int) -> List[Dict[str, Any]]:
    q = q.strip()
    if not q:
        return []
    like = f"%{q}%"
    with _conn() as con:
        rows = con.execute(
            """
            SELECT id, content, tags, ts
            FROM memories
            WHERE content LIKE ? OR tags LIKE ?
            ORDER BY ts DESC
            LIMIT ?
            """,
            (like, like, int(top_k)),
        ).fetchall()
    return [dict(r) for r in rows]

# ---------- FastAPI ----------
app = FastAPI(title="OathLink Backend", version="0.1.0")

def _check_auth(x_auth_token: Optional[str]):
    if AUTH_TOKEN_ENV:
        if not x_auth_token or x_auth_token != AUTH_TOKEN_ENV:
            raise HTTPException(status_code=401, detail="Unauthorized")

# ---------- Schemas ----------
class MemoryWrite(BaseModel):
    content: str
    tags: Optional[List[str]] = None

class ComposeReq(BaseModel):
    input: str
    tags: Optional[List[str]] = None
    top_k: int = 5

# ---------- Routes (health & memory) ----------
@app.get("/health")
def healthcheck():
    return {"ok": True, "ts": time.time()}

@app.post("/memory/write")
def memory_write(
    body: MemoryWrite,
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
):
    _check_auth(x_auth_token)
    mid = write_memory(body.content, body.tags)
    return {"ok": True, "id": mid}

@app.get("/memory/search")
def memory_search(
    q: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=100),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
):
    _check_auth(x_auth_token)
    hits = search_memory(q, top_k)
    return {"ok": True, "results": hits, "ts": time.time()}

# ---------- Compose helper ----------
def _compose_core(req: ComposeReq):
    q = (" ".join(req.tags or []) + " " + req.input).strip()
    hits = search_memory(q or req.input, req.top_k)
    ctx_block = "\n".join([f"- {h['content']}" for h in hits]) or "（無匹配的過往記憶）"
    user = f"【當前輸入】\n{req.input}\n\n【可用記憶】\n{ctx_block}"
    prompt = f"{PERSONA_PROMPT}\n\n{user}\n\n請輸出最終回覆："
    return {"prompt": prompt, "hits": hits}

# ---------- Two compose endpoints for testing ----------
@app.post("/compose1", summary="Compose (variant 1)")
def compose1(
    req: ComposeReq,
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
):
    _check_auth(x_auth_token)
    data = _compose_core(req)
    return {
        "ok": True,
        "variant": "compose1",
        "prompt": data["prompt"],
        "context_hits": data["hits"],
        "output": "（compose1：本地拼接完成）",
        "ts": time.time(),
    }

@app.post("/compose2", summary="Compose (variant 2)")
def compose2(
    req: ComposeReq,
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
):
    _check_auth(x_auth_token)
    data = _compose_core(req)
    return {
        "ok": True,
        "variant": "compose2",
        "prompt": data["prompt"],
        "context_hits": data["hits"],
        "output": "（compose2：本地拼接完成）",
        "ts": time.time(),
    }