# app.py  —— 只有 /health 與 /memory/write
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
import os, json, time, sqlite3, pathlib

APP_NAME = "OathLink Backend"
DB_PATH = os.getenv("DB_PATH", "/app/data/memory.db")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "jacksungtw")  # 您可改掉

app = FastAPI(title=APP_NAME, version="0.1.0")

# --- 簡單 SQLite，僅供 memory.write ---
pathlib.Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute("""CREATE TABLE IF NOT EXISTS memory(
  id TEXT PRIMARY KEY,
  content TEXT NOT NULL,
  tags TEXT,
  ts REAL
)""")
conn.commit()

class MemoryWriteReq(BaseModel):
    content: str
    tags: Optional[list[str]] = None

def _check(x_auth_token: Optional[str]):
    if AUTH_TOKEN and x_auth_token != AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/health", summary="Healthcheck")
def healthcheck():
    return {"ok": True, "ts": time.time()}

@app.post("/memory/write", summary="Memory Write")
def memory_write(req: MemoryWriteReq,
                 x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
    _check(x_auth_token)
    mid = os.popen("uuidgen").read().strip() or str(time.time())
    conn.execute(
        "INSERT INTO memory(id, content, tags, ts) VALUES(?,?,?,?)",
        (mid, req.content, json.dumps(req.tags or []), time.time())
    )
    conn.commit()
    return {"ok": True, "id": mid}