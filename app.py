# app.py
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import os, sqlite3, uuid, time, json

# ---------- 基本設定 ----------
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "<jacksungtw>")  # 與您測試用的一致
DB_PATH    = os.getenv("DB_PATH", "data/memory.db")

app = FastAPI(title="OathLink Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# ---------- SQLite ----------
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

# ---------- 小工具 ----------
def must_auth(x_auth_token: Optional[str]):
    if AUTH_TOKEN and x_auth_token != AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

def add_memory(content: str, tags: Optional[List[str]]) -> str:
    mid = str(uuid.uuid4())
    ts  = time.time()
    tags_json = json.dumps(tags or [])
    CONN.execute(
        "INSERT INTO memories(id, content, tags, ts) VALUES (?,?,?,?)",
        (mid, content, tags_json, ts)
    )
    CONN.commit()
    return mid

def search_memory(q: str, top_k: int = 5) -> List[Dict[str, Any]]:
    q_like = f"%{q}%"
    rows = CONN.execute(
        "SELECT id, content, tags, ts FROM memories "
        "WHERE content LIKE ? OR tags LIKE ? "
        "ORDER BY ts DESC LIMIT ?",
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

def health_ok() -> bool:
    try:
        CONN.execute("SELECT 1").fetchone()
        return True
    except Exception:
        return False

# ---------- Routes ----------
@app.get("/health")
def health():
    return {"ok": health_ok(), "ts": time.time()}

@app.post("/memory/write")
def memory_write(payload: Dict[str, Any], x_auth_token: Optional[str] = Header(None, alias="X-Auth-Token")):
    must_auth(x_auth_token)
    content = str(payload.get("content", "")).strip()
    tags    = payload.get("tags") or []
    if not content:
        raise HTTPException(422, detail="content is required")
    mid = add_memory(content, tags)
    return {"ok": True, "id": mid}

@app.get("/memory/search")
def memory_search(
    q: str = Query(""),
    top_k: int = Query(5, ge=1, le=50),
    x_auth_token: Optional[str] = Header(None, alias="X-Auth-Token")
):
    must_auth(x_auth_token)
    return {"results": search_memory(q, top_k)}

@app.post("/compose")
def compose(payload: Dict[str, Any], x_auth_token: Optional[str] = Header(None, alias="X-Auth-Token")):
    must_auth(x_auth_token)
    user_input = str(payload.get("input", "")).strip()
    tags       = payload.get("tags") or []
    top_k      = int(payload.get("top_k", 5))

    hits = search_memory(user_input, top_k)
    mem_lines = []
    for h in hits:
        t = ",".join(h.get("tags") or [])
        mem_lines.append(f"- [{t}] {h['content']}")
    mem_block = "\n".join(mem_lines) if mem_lines else "(無相關記憶)"

    persona = (
        "你是 OathLink 的專屬助理，必須保持穩定的語氣與邏輯。"
        "使用敬語（稱呼對方為「師父」或「您」），回覆務實、有條理。"
    )
    prompt = (
        f"{persona}\n\n"
        f"【相關記憶】\n{mem_block}\n\n"
        f"【使用者輸入】\n{user_input}\n\n"
        f"請先給出直接可用的回覆（同時維持一貫的語風），必要時再列出後續步驟。"
    )
    return {"ok": True, "prompt": prompt, "tags": tags, "top_k": top_k}