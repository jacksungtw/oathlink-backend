from typing import Optional, List
from pydantic import BaseModel
from fastapi import Header

class ComposeReq(BaseModel):
    input: str
    tags: Optional[List[str]] = None
    top_k: int = 5

@app.post("/compose", summary="Compose with persona + memory")
def compose(req: ComposeReq, x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token")):
    _check(x_auth_token)  # 若您暫時不驗證，可先註解這行

    # 先把記憶搜尋起來（沒有也不會出錯）
    q = (" ".join(req.tags or []) + " " + req.input).strip()
    hits = search_memory(q or req.input, req.top_k)
    ctx_block = "\n".join([h["content"] for h in hits]) if hits else "(no memory)"

    # 回傳一個可見的結果，保證 /compose 可用
    return {
        "ok": True,
        "input": req.input,
        "tags": req.tags or [],
        "used_memory": hits,
        "preview": f"[persona]\n[ctx]\n{ctx_block}\n[reply]\n(這裡先回假輸出，確認路由 OK)"
    }