# app.py
import os, time, json, sqlite3, uuid
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException, Header, Query
from pydantic import BaseModel

DB_PATH = os.getenv("DB_PATH", "data/memory.db")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "changeme")

app = FastAPI(title="OathLink Backend")

# --- storage helpers ---
def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def get_conn() -> sqlite3.Connection:
    _ensure_dir(DB_PATH)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS memories(
      id TEXT PRIMARY KEY,
      content TEXT NOT NULL,
      tags TEXT NOT NULL,
      ts REAL NOT NULL
    )
    """)
    conn.commit()
    return conn

CONN = get_conn()

def add_memory(content: str, tags: Optional[List[str]] = None) -> str:
    mid = str(uuid.uuid4())
    ts = time.time()
    tags_json = json.dumps(tags or [])
    CONN.execute("INSERT INTO memories(id,content,tags,ts) VALUES(?,?,?,?)",
                 (mid, content, tags_json, ts))
    CONN.commit()
    return mid

def search_memory(q: str, top_k: int = 5) -> List[Dict[str, Any]]:
    q_like = f"%{q}%"
    rows = CONN.execute(
        "SELECT id, content, tags, ts FROM memories "
        "WHERE content LIKE ? OR tags LIKE ? ORDER BY ts DESC LIMIT ?",
        (q_like, q_like, top_k)
    ).fetchall()
    out = []
    for rid, content, tags_json, ts in rows:
        try:
            tags = json.loads(tags_json) if tags_json else []
        except Exception:
            tags = []
        out.append({"id": rid, "content": content, "tags": tags, "ts": ts})
    return out

# --- auth guard ---
def require_auth(x_auth_token: str | None):
    if AUTH_TOKEN and (x_auth_token is None or x_auth_token != AUTH_TOKEN):
        raise HTTPException(status_code=401, detail="Unauthorized")

# --- models ---
class WriteBody(BaseModel):
    content: str
    tags: Optional[List[str]] = None

class ComposeBody(BaseModel):
    input: str
    tags: Optional[List[str]] = None
    top_k: int = 5

# --- routes ---
@app.get("/health")
def health():
    return {"ok": True, "ts": time.time()}

@app.post("/memory/write")
def memory_write(body: WriteBody, x_auth_token: str | None = Header(default=None, alias="X-Auth-Token")):
    require_auth(x_auth_token)
    mid = add_memory(body.content, body.tags)
    return {"ok": True, "id": mid}

@app.get("/memory/search")
def memory_search(q: str = Query(...), top_k: int = Query(5), x_auth_token: str | None = Header(default=None, alias="X-Auth-Token")):
    require_auth(x_auth_token)
    hits = search_memory(q, top_k)
    return {"results": hits, "ok": True, "ts": time.time()}

# 人格模板 + 記憶組合
PERSONA = os.getenv("PERSONA_PROMPT", "你是 OathLink 助理，語氣穩定、精簡、禮貌，回覆使用者偏好。")
@app.post("/compose")
def compose(body: ComposeBody, x_auth_token: str | None = Header(default=None, alias="X-Auth-Token")):
    require_auth(x_auth_token)
    hits = search_memory(body.input, body.top_k)
    memory_block = "\n".join([f"- {h['content']}" for h in hits]) or "- （無匹配記憶）"
    prompt = (
        f"{PERSONA}\n\n"
        f"【相關記憶】\n{memory_block}\n\n"
        f"【使用者輸入】\n{body.input}\n\n"
        f"請根據人格與相關記憶回覆。"
    )
    return {"ok": True, "prompt": prompt, "hits": hits, "ts": time.time()}