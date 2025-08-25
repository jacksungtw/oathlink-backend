import json, requests, unicodedata
import streamlit as st

st.set_page_config(page_title="OathLink /compose 即時測試", layout="centered")

# ---- 側邊欄：連線設定 ----
st.sidebar.header("連線設定")
base_url = st.sidebar.text_input(
    "Backend Base URL",
    value="https://oathlink-backend-clean-production.up.railway.app",
    help="例如：https://<your-app>.up.railway.app",
)
auth_token = st.sidebar.text_input("X-Auth-Token（可留空）", type="password")
timeout_s = st.sidebar.number_input("逾時秒數", min_value=5, max_value=120, value=30)
show_raw = st.sidebar.checkbox("顯示原始 JSON", value=False)

st.title("🧪 OathLink /compose 即時測試")

# ---- 輸入區 ----
input_text = st.text_area("問題／指令（必填）", height=140, placeholder="請條列三點進度，並標註下一步")
tags_str = st.text_input("Tags（逗號分隔，可留空）", value="clean,demo")
top_k = st.slider("top_k", min_value=1, max_value=20, value=5)

col_run, col_sample = st.columns([1,1])
with col_sample:
    if st.button("載入示例"):
        st.session_state["input_text"] = "請條列三點進度，並標註下一步"
        st.session_state["tags_str"] = "clean,demo"
        st.rerun()

# 從 session 還原示例（若有）
if "input_text" in st.session_state:
    input_text = st.session_state.pop("input_text")
    st.session_state["input_text_applied"] = input_text
if "tags_str" in st.session_state:
    tags_str = st.session_state.pop("tags_str")
    st.session_state["tags_str_applied"] = tags_str

def to_tags(s: str):
    if not s: return None
    arr = [t.strip() for t in s.split(",") if t.strip()]
    return arr if arr else None

def call_compose(base: str, token: str | None, text: str, tags: list[str] | None, k: int, timeout: int):
    url = base.rstrip("/") + "/compose"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["X-Auth-Token"] = token
    payload = {"input": text, "top_k": k}
    if tags:
        payload["tags"] = tags
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    r = requests.post(url, headers=headers, data=data, timeout=timeout)
    # 優先回傳伺服器原文錯誤
    r.raise_for_status()
    return r.json()

with col_run:
    clicked = st.button("🚀 呼叫 /compose")
if clicked:
    if not base_url.strip():
        st.error("請先填 Base URL")
    elif not input_text.strip():
        st.error("請先輸入問題／指令")
    else:
        try:
            tags = to_tags(tags_str)
            resp = call_compose(base_url, auth_token, input_text.strip(), tags, top_k, timeout_s)

            st.success("✅ /compose 呼叫成功")
            # 顯示主要輸出
            st.subheader("回覆 output")
            # 有些環境回來可能帶有亂碼，但 Streamlit 端顯示多為正常中文
            out = resp.get("output", "")
            # 嘗試規範化（對個別字元異常較友善）
            out = unicodedata.normalize("NFC", out)
            st.write(out)

            # 顯示命中記憶
            hits = resp.get("context_hits") or []
            st.markdown("**命中記憶（context_hits）**")
            if hits:
                for i, h in enumerate(hits, 1):
                    with st.expander(f"Hit #{i} — {h.get('id','')[:8]}…"):
                        st.write(f"**content**: {h.get('content','')}")
                        st.write(f"**tags**: {h.get('tags',[])}")
                        st.write(f"**ts**: {h.get('ts')}")
            else:
                st.caption("（無）")

            # 顯示 prompt（system / user）
            with st.expander("查看 prompt（system / user）"):
                p = resp.get("prompt", {})
                st.code(p.get("system", ""), language="text")
                st.code(p.get("user", ""), language="text")

            # 顯示 model / search mode
            meta_cols = st.columns(3)
            meta_cols[0].metric("model_used", str(resp.get("model_used")))
            meta_cols[1].metric("search_mode", str(resp.get("search_mode", "default")))
            meta_cols[2].metric("ok", str(resp.get("ok")))

            # 原始 JSON
            if show_raw:
                st.subheader("Raw JSON")
                st.json(resp)

            # 方便複製的 curl
            with st.expander("複製 cURL（重現同一請求）"):
                curl_headers = f'-H "Content-Type: application/json; charset=utf-8"'
                if auth_token:
                    curl_headers += f' -H "X-Auth-Token: {auth_token}"'
                curl = (
                    f'curl -X POST "{base_url.rstrip("/")}/compose" '
                    f'{curl_headers} '
                    f"-d '{json.dumps({'input': input_text.strip(), 'tags': tags or [], 'top_k': top_k}, ensure_ascii=False)}'"
                )
                st.code(curl, language="bash")

        except requests.HTTPError as he:
            st.error(f"HTTP {he.response.status_code}：{he.response.text}")
        except Exception as e:
            st.error(f"請求失敗：{e}")