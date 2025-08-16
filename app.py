# app.py
import os
import time
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel

# 本地簡易儲存（SQLite）——已在您的 storage.py 實作
import storage

# --- 可選：OpenAI（若未設 OPENAI_API_KEY 會自動跳過） ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_OPENAI = bool(OPENAI_API_KEY)
if USE_OPENAI:
    try:
        from openai import OpenAI
        oai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        USE_OPENAI = False

# 服務啟動
app = FastAPI(
    title="OathLink 後端",
    version="0.1.0",
    description="固定語風 + 持久化記憶 + 可替換引擎 的極簡後端"
)

# ---- 簡單權杖驗證（與您現有流程一致） ----
EXPECTED_TOKEN = os.getenv("X_AUTH_TOKEN", "")  # 您在 Railway 設定的變數
def _check_token(x_auth_token: Optional[str]):
    if EXPECTED_TOKEN and x_auth_token != EXPECTED_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

# ---- 資料模型 ----
class MemoryWrite(BaseModel):
    content: str
    tags: Optional[List[str]] = None

class MemoryItem(BaseModel):
    id: str
    content: str
    tags: List[str] = []
    ts: float

class ComposeRequest(BaseModel):
    input: str
    tags: Optional[List[str]] = None
    top_k: int = 5

class ComposeResponse(BaseModel):
    ok: bool
    prompt: str
    memories: List[MemoryItem] = []
    output: str
    ts: float

# ---- 健康檢查 ----
@app.get("/health", summary="Healthcheck")
def health():
    return {"ok": storage.health(), "ts": time.time()}

# ---- 寫記憶 ----
@app.post("/memory/write", summary="Memory Write")
def memory_write(
    body: MemoryWrite,
    x_auth_token: Optional[str] = Header(None, convert_underscores=False),
):
    _check_token(x_auth_token)
    mid = storage.add_memory(body.content, body.tags or [])
    return {"ok": True, "id": mid}

# ---- 搜記憶 ----
@app.get("/memory/search", summary="Memory Search")
def memory_search(
    q: str = Query("", description="查詢字串"),
    top_k: int = Query(3, ge=1, le=20),
    x_auth_token: Optional[str] = Header(None, convert_underscores=False),
):
    _check_token(x_auth_token)
    rows = storage.search_memory(q=q, top_k=top_k)
    return {"results": rows}

# ---- 新增：組合提示 +（可選）生成 ----
@app.post("/compose", response_model=ComposeResponse, summary="Compose reply from persona + memory")
def compose(
    body: ComposeRequest,
    x_auth_token: Optional[str] = Header(None, convert_underscores=False),
):
    _check_token(x_auth_token)

    # 1) 取相關記憶
    mem_rows = storage.search_memory(q=body.input, top_k=body.top_k)
    mem_items: List[MemoryItem] = []
    for r in mem_rows:
        mem_items.append(
            MemoryItem(
                id=r.get("id", ""),
                content=r.get("content", ""),
                tags=r.get("tags", []),
                ts=r.get("ts", 0.0),
            )
        )

    # 2) 人格模板（可自行調整成您固定語風）
    persona = (
        "你是 OathLink 的助手，稱呼使用者為『師父』或『您』，"
        "語氣尊重、清楚、步驟式，回答務必精簡可執行。"
    )

    # 3) 將記憶轉成可注入的 context
    memory_context_lines = []
    for i, m in enumerate(mem_items, start=1):
        t = ", ".join(m.tags) if m.tags else ""
        memory_context_lines.append(f"{i}. {m.content}  [tags: {t}]")

    memory_context = "\n".join(memory_context_lines) if memory_context_lines else "(無匹配記憶)"

    # 4) 產生最終 Prompt（即使沒 OpenAI 也回傳，方便前端或鍵盤直接使用）
    final_prompt = (
        f"{persona}\n\n"
        f"【相關記憶】\n{memory_context}\n\n"
        f"【使用者輸入】\n{body.input}\n\n"
        f"請依人格模板，給出最精簡、可直接複製使用的回覆。"
    )

    # 5) 可選：用 OpenAI 直接生成（如果有 API Key）
    output_text = ""
    if USE_OPENAI:
        try:
            resp = oai_client.chat.completions.create(
                model=os.getenv("COMPOSE_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": persona},
                    {"role": "user", "content": f"相關記憶：\n{memory_context}"},
                    {"role": "user", "content": f"使用者輸入：\n{body.input}\n請直接給可複製的最終回覆。"},
                ],
                temperature=float(os.getenv("COMPOSE_TEMPERATURE", "0.4")),
            )
            output_text = resp.choices[0].message.content.strip()
        except Exception as e:
            # 若模型失敗，不阻斷；回傳 prompt 讓前端自行處理
            output_text = f"(生成暫停：{e})"

    return ComposeResponse(
        ok=True,
        prompt=final_prompt,
        memories=mem_items,
        output=output_text,
        ts=time.time(),
    )