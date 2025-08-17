# app.py — OathLink Backend (含 /compose)
import os
import time
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

# 連結既有儲存層（您 repo 已有 storage.py）
from storage import add_memory, search_memory, health as storage_health

app = FastAPI(title="OathLink Backend", version="1.0.0")

# ====== 安全設定 ======
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "").strip()

def _check(token: Optional[str]) -> None:
    if not AUTH_TOKEN:  # 未設定則視為關閉驗證（便於本機測試）
        return
    if not token or token.strip() != AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

# ====== 資料模型 ======
class MemoryWrite(BaseModel):
    content: str = Field(..., min_length=1)
    tags: Optional[List[str]] = None

class ComposeReq(BaseModel):
    input: str = Field(..., min_length=1)
    tags: Optional[List[str]] = None
    top_k: int = 5

# ====== 固定人格模板 ======
PERSONA_PROMPT = (
    "你是 OathLink 的專屬助手，語氣穩定、尊敬、簡潔，稱呼用「師父／您／願主」。"
    "請先結論後理由；不得使用不敬語；輸出採繁體中文。"
)

# ====== 健康檢查 ======
@app.get("/health", summary="Healthcheck")
def health():
    ok = True
    try:
        ok = bool(storage_health())
    except Exception:
        ok = False
    return {"ok": ok, "ts": time.time()}

# ====== 記憶：寫入 ======
@app.post("/memory/write", summary="Memory Write")
def memory_write(
    body: MemoryWrite,
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
):
    _check(x_auth_token)
    mid = add_memory(body.content, body.tags or [])
    return {"ok": True, "id": mid, "ts": time.time()}

# ====== 記憶：搜尋 ======
@app.get("/memory/search", summary="Memory Search")
def memory_search(
    q: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=100),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
):
    _check(x_auth_token)
    hits = search_memory(q, top_k)
    return {"ok": True, "results": hits, "ts": time.time()}

# ====== 組合：人格＋記憶（可選代叫 OpenAI） ======
@app.post("/compose", summary="Compose with persona + memory")
def compose(
    req: ComposeReq,
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
):
    _check(x_auth_token)

    # 1) 以「輸入＋標籤」組查詢並檢索記憶
    q = (" ".join(req.tags or []) + " " + req.input).strip()
    hits = search_memory(q or req.input, req.top_k)

    ctx_block = "\n".join([f"- {h['content']}" for h in hits]) if hits else "（無匹配記憶）"

    # 2) 最小可用 prompt（即使無模型也能回）
    system = PERSONA_PROMPT
    user = f"【當前輸入】\n{req.input}\n\n【可用記憶】\n{ctx_block}"
    prompt = f"{system}\n\n{user}\n\n【請以人格口吻輸出】"

    # 3) 若有 OPENAI_API_KEY，嘗試代叫；失敗不影響回傳
    output: Optional[str] = None
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
    MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if OPENAI_API_KEY:
        try:
            from openai import OpenAI  # pip install openai>=1
            client = OpenAI(api_key=OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                temperature=0.3,
            )
            output = resp.choices[0].message.content
        except Exception:
            output = None  # 不中斷，回本地 prompt

    return {"ok": True, "prompt": prompt, "model_output": output, "hits": hits, "ts": time.time()}