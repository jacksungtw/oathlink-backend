# storage.py
import os, sqlite3, uuid, time, json
from typing import List, Dict, Any

DB_PATH = os.getenv("DB_PATH", "data/memory.db")

def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def get_conn() -> sqlite3.Connection:
    _ensure_dir(DB_PATH)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            tags TEXT NOT NULL,
            ts REAL NOT NULL
        )
        """
    )
    conn.commit()
    return conn

CONN = get_conn()

def add_memory(content: str, tags: List[str] | None = None) -> str:
    mid = str(uuid.uuid4())
    ts = time.time()
    tags_json = json.dumps(tags or [])
    CONN.execute(
        "INSERT INTO memories (id, content, tags, ts) VALUES (?, ?, ?, ?)",
        (mid, content, tags_json, ts),
    )
    CONN.commit()
    return mid

def search_memory(q: str, top_k: int = 5) -> List[Dict[str, Any]]:
    q_like = f"%{q}%"
    rows = CONN.execute(
        """
        SELECT id, content, tags, ts
        FROM memories
        WHERE content LIKE ? OR tags LIKE ?
        ORDER BY ts DESC
        LIMIT ?
        """,
        (q_like, q_like, top_k),
    ).fetchall()

    out: List[Dict[str, Any]] = []
    for rid, content, tags_json, ts in rows:
        try:
            tags = json.loads(tags_json) if tags_json else []
        except Exception:
            tags = []
        out.append({"id": rid, "content": content, "tags": tags, "ts": ts})
    return out

def health() -> bool:
    try:
        CONN.execute("SELECT 1").fetchone()
        return True
    except Exception:
        return False
