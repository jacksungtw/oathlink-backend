mport os, json, sqlite3, time, unicodedata, re
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Header, HTTPException, Body, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

APP_TITLE   = "OathLink Backend"
APP_VERSION = "0.5.0"

# =========================
# FastAPI & CORS
# =========================
app = FastAPI(title=APP_TITLE, version=APP_VERSION)

ALLOWED_ORIGINS = [
    "http://localhost:8501",
    "http://127.0.0.1:8501",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*",  # 開發期放寬，正式環境請收斂
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 額外保險：處理所有未定義路徑的 OPTIONS，避免 405
@app.options("/{full_path:path}", include_in_schema=False)
async def options_catch_all(full_path: str) -> Response:
    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS,PATCH",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "600",
        },
    )

# =========================
# 環境變數
# =========================
AUTH_TOKEN     = (os.getenv("X_AUTH_TOKEN") or os.getenv("AUTH_TOKEN") or "abc123").strip()
DB_PATH        = os.getenv("DB_PATH", "data/oathlink.db")
SEARCH_MODE    = (os.getenv("SEARCH_MODE") or "like").lower()  # like | fts（本版預設 like）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# =========================
# JSON 回傳：強制 UTF-8 / 非 ASCII 不轉義
# =========================
def json_utf8(payload: Any, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        content=payload,
        status_code=status_code,
        media_type="application/json; charset=utf-8",
        # 以 dumps 覆寫確保 ensure_ascii=False
        dumps=lambda obj: json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    )

# =========================
# 資料庫
# =========================
os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
con = sqlite3.connect(DB_PATH, check_same_thread=False)
con.row_factory = sqlite3.Row
# 重要：不覆寫 text_factory，維持 sqlite3 預設（UTF-8）
cur = con.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS memory (
  id    TEXT PRIMARY KEY,
  content TEXT NOT NULL,
  tags    TEXT,
  ts      REAL NOT NULL
);
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS kv (
  k TEXT PRIMARY KEY,
  v TEXT NOT NULL
);
""")
con.commit()

def _now() -> float:
    return time.time()

def _mk_id() -> str:
    import uuid
    return str(uuid.uuid4())

def _norm(s: str) -> str:
    # 僅做正規化，不做任何 encode/decode，避免產生亂碼
    return unicodedata.normalize("NFKC", s or "")

def _write_memory(content: str, tags: List[str], ts: Optional[float] = None) -> str:
    mid = _mk_id()
    cur.execute(
        "INSERT INTO memory (id, content, tags, ts) VALUES (?,?,?,?)",
        (mid, _norm(content), json.dumps(tags or [], ensure_ascii=False), ts or _now())
    )
    con.commit()
    return mid

def _row_to_mem(r: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": r["id"],
        "content": r["content"],  # 直接以 str 回傳
        "tags": json.loads(r["tags"] or "[]"),
        "ts": r["ts"],
    }

def _search_like(q: str, top_k: int) -> List[Dict[str, Any]]:
    like = f"%{_norm(q)}%"
    rows = cur.execute(
        "SELECT id, content, tags, ts FROM memory WHERE content LIKE ? OR tags LIKE ? ORDER BY ts DESC LIMIT ?",
        (like, like, max(1, top_k))
    ).fetchall()
    return [_row_to_mem(r) for r in rows]

def _search_memory(q: str, top_k: int) -> List[Dict[str, Any]]:
    # 本版預設以 LIKE 搜，FTS 有需要再擴充
    return _search_like(q, top_k)

# =========================
# 權限
# =========================
def _guard(token: Optional[str]):
    if AUTH_TOKEN:
        if not token or token != AUTH_TOKEN:
            raise HTTPException(status_code=401, detail="Unauthorized")

# =========================
# 路由：基本 / 健康 / 列路由
# =========================
@app.get("/", summary="Root")
def root():
    return json_utf8({
        "ok": True,
        "service": APP_TITLE,
        "version": APP_VERSION,
        "search_mode": SEARCH_MODE,
        "paths": [r.path for r in app.router.routes],
        "ts": _now(),
    })

@app.get("/health", summary="Healthcheck")
def health():
    return json_utf8({"ok": True, "ts": _now()})

@app.get("/routes", summary="List routes")
def routes():
    return json_utf8({"ok": True, "routes": [r.path for r in app.router.routes], "ts": _now()})

# =========================
# 路由：Debug / Echo / Reset / Peek / Mojibake 修復
# =========================
@app.post("/debug/echo", summary="Echo back raw JSON for UTF-8 diagnostics")
async def debug_echo(request: Request, x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
    _guard(x_auth_token)
    raw = await request.body()
    as_text_utf8 = raw.decode("utf-8", errors="replace")
    parsed: Any = None
    try:
        parsed = json.loads(as_text_utf8)
    except Exception:
        parsed = None
    first = raw[:24]
    return json_utf8({
        "ok": True,
        "raw_len": len(raw),
        "raw_first_24_bytes_hex": first.hex(),
        "as_text_utf8": as_text_utf8,
        "parsed": parsed,
        "ts": _now()
    })

@app.post("/debug/reset", summary="Danger: clear all memory")
def debug_reset(x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
    _guard(x_auth_token)
    cur.execute("DELETE FROM memory;")
    con.commit()
    return json_utf8({"ok": True, "reset": True, "ts": _now()})

@app.get("/debug/peek", summary="Peek last 50 memory rows")
def debug_peek(x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
    _guard(x_auth_token)
    rows = cur.execute("SELECT * FROM memory ORDER BY ts DESC LIMIT 50").fetchall()
    items = [_row_to_mem(r) for r in rows]
    return json_utf8({"ok": True, "rows": items, "ts": _now()})

# 嘗試修復典型 mojibake：「UTF-8 被當成 latin-1 解析」
def _looks_mojibake(s: str) -> bool:
    # 常見亂碼特徵：大量 â ä å æ ç 等出現
    return bool(re.search(r"[âäåæçø¤¦¨´`˜ˆ]", s))

def _has_cjk(s: str) -> bool:
    return any('\u4e00' <= ch <= '\u9fff' for ch in s)

def _repair_once(s: str) -> Optional[str]:
    # 只嘗試 latin-1 -> utf-8 回轉
    try:
        repaired = s.encode("latin-1").decode("utf-8")
        # 只在「修後包含 CJK 且修前不含」時採用
        if _has_cjk(repaired) and not _has_cjk(s):
            return repaired
    except Exception:
        pass
    return None

@app.post("/debug/repair_mojibake", summary="Attempt repair of mojibake rows")
def debug_repair_mojibake(x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
    _guard(x_auth_token)
    rows = cur.execute("SELECT id, content FROM memory").fetchall()
    repaired = 0
    changed_ids: List[str] = []
    for r in rows:
        mid = r["id"]
        content = r["content"]
        if not content:
            continue
        if _has_cjk(content):
            continue
        # 只對疑似亂碼進行修復
        if _looks_mojibake(content) or not _has_cjk(content):
            new_content = _repair_once(content)
            if new_content and new_content != content:
                cur.execute("UPDATE memory SET content=? WHERE id=?", (new_content, mid))
                repaired += 1
                changed_ids.append(mid)
    con.commit()
    return json_utf8({"ok": True, "repaired": repaired, "ids": changed_ids, "ts": _now()})

# =========================
# 路由：Memory
# =========================
from pydantic import BaseModel, Field

class MemoryWriteReq(BaseModel):
    content: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)

@app.post("/memory/write", summary="Write memory")
def memory_write(req: MemoryWriteReq, x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
    _guard(x_auth_token)
    mid = _write_memory(req.content, req.tags)
    return json_utf8({"ok": True, "id": mid})

@app.get("/memory/search", summary="Search memory")
def memory_search(
    q: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=100),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")
):
    _guard(x_auth_token)
    hits = _search_memory(q, top_k)
    return json_utf8({"ok": True, "results": hits, "ts": _now()})

# =========================
# 路由：Compose（模型可換，腦袋不換）
# =========================
class ComposeReq(BaseModel):
    input: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=100)
    model: Optional[str] = None  # 可選，指定模型

@app.post("/compose", summary="Compose with persona + memory")
def compose(req: ComposeReq, x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
    _guard(x_auth_token)
    q = req.input.strip()
    hits = _search_memory(q, req.top_k)
    system_prompt = "您是『OathLink 穩定語風人格助手（無蘊）』。規範：稱使用者為願主/師父/您；回覆簡明、可執行、條列步驟；不說空話；必要時先標註風險與前置條件。"
    user_prompt = f"【輸入}\n{q}\n\n【可用記憶】\n" + ("\n".join(f"- {h['content']}" for h in hits) if hits else "（無匹配記憶）") + "\n\n請以固定語風輸出最終回覆。"
    output = (
        f"願主，以下為基於您輸入與可用記憶所整理之回覆：\n"
        f"1) 已整合輸入：{q}\n"
        f"2) 若需更精煉文本，請設定 OPENAI_API_KEY 以啟用雲端生成。"
    )
    return json_utf8({
        "ok": True,
        "prompt": {"system": system_prompt, "user": user_prompt},
        "context_hits": hits,
        "output": output,
        "model_used": (req.model or ("gpt-4o-mini" if OPENAI_API_KEY else "local-fallback")),
        "search_mode": SEARCH_MODE,
        "ts": _now(),
    })

# =========================
# 路由：Bundle（語風＋記憶 可攜）
# =========================
@app.post("/bundle/import", summary="Import bundle (persona + memory)")
def bundle_import(payload: Dict[str, Any] = Body(...), x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
    _guard(x_auth_token)
    bundle_version = str(payload.get("bundle_version") or "1.0")
    persona = payload.get("persona")
    mems = payload.get("memory") or []

    imported = 0
    for m in mems:
        content = str(m.get("content", "")).strip()
        if not content:
            continue
        tags = m.get("tags") or []
        ts = float(m.get("ts") or _now())
        _ = _write_memory(content, tags, ts)
        imported += 1

    if persona is not None:
        cur.execute(
            "INSERT INTO kv (k,v) VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
            ("persona", json.dumps(persona, ensure_ascii=False))
        )
        con.commit()

    return json_utf8({"ok": True, "imported": imported, "skipped": 0, "bundle_version": bundle_version, "ts": _now()})

@app.get("/bundle/export", summary="Export bundle (persona + memory)")
def bundle_export(x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
    _guard(x_auth_token)
    persona_row = cur.execute("SELECT v FROM kv WHERE k='persona'").fetchone()
    persona = json.loads(persona_row["v"]) if persona_row else {"name": "無蘊-敬語版"}
    rows = cur.execute("SELECT id, content, tags, ts FROM memory ORDER BY ts DESC").fetchall()
    mem = [_row_to_mem(r) for r in rows]
    return json_utf8({
        "ok": True,
        "bundle_version": "1.0",
        "persona": persona,
        "memory": mem,
        "count": len(mem),
        "ts": _now()
    })

@app.get("/bundle/preview", summary="Preview bundle summary")
def bundle_preview(x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
    _guard(x_auth_token)
    persona_row = cur.execute("SELECT v FROM kv WHERE k='persona'").fetchone()
    persona = json.loads(persona_row["v"])["name"] if persona_row else "無蘊-敬語版"
    row = cur.execute("SELECT COUNT(*) AS c, MAX(ts) AS t FROM memory").fetchone()
    return json_utf8({
        "ok": True,
        "persona": persona,
        "count_memory": row["c"] or 0,
        "latest_ts": row["t"],
        "sample": [m for m in cur.execute("SELECT id, content, tags, ts FROM memory ORDER BY ts DESC LIMIT 3")],
    })    