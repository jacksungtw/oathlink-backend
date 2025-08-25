import json
import requests
import streamlit as st

st.set_page_config(page_title="OathLink 記憶 Debug", page_icon="🧠", layout="centered")
st.title("🧠 OathLink 記憶 Debug（/memory/write ＆ /memory/search）")

# === 基本連線設定 ===
base_url = st.text_input("Backend Base URL", "https://oathlink-backend-clean-production.up.railway.app")
token    = st.text_input("X-Auth-Token（若後端有啟用 AUTH_TOKEN 就必填）", type="password", help="Railway Variables 內的 AUTH_TOKEN 值")

headers = {"Content-Type": "application/json; charset=utf-8"}
if token:
    headers["X-Auth-Token"] = token

st.divider()

# === 寫入記憶 /memory/write ===
st.subheader("✍️ 寫入記憶（POST /memory/write）")
col1, col2 = st.columns(2)
with col1:
    mw_content = st.text_area("content（必填）", "這是一筆測試記憶：清單測試")
with col2:
    mw_tags_raw = st.text_input("tags（逗號分隔，可留空）", "clean,demo")

if st.button("寫入一筆記憶"):
    body = {
        "content": mw_content,
        "tags": [t.strip() for t in mw_tags_raw.split(",") if t.strip()]
    }
    try:
        resp = requests.post(f"{base_url}/memory/write", headers=headers, data=json.dumps(body), timeout=30)
        st.code(resp.text, language="json")
        if resp.ok:
            rid = resp.json().get("id")
            st.success(f"✅ 寫入成功，id = {rid}")
        else:
            st.error(f"❌ 寫入失敗：HTTP {resp.status_code}")
    except Exception as e:
        st.error(f"請求例外：{e}")

    # 對應的 cURL（可複製）
    curl = (
        'curl -X POST "{u}/memory/write" \\\n'
        '  -H "Content-Type: application/json; charset=utf-8" \\\n'
        '{tok}'
        "  -d '{body}'"
    ).format(
        u=base_url.rstrip("/"),
        tok=('  -H "X-Auth-Token: {t}" \\\n'.format(t=token) if token else ""),
        body=json.dumps(body, ensure_ascii=False)
    )
    st.caption("重現同請求（cURL）：")
    st.code(curl, language="bash")

st.divider()

# === 搜尋記憶 /memory/search ===
st.subheader("🔎 搜尋記憶（GET /memory/search）")
col3, col4 = st.columns([3,1])
with col3:
    q = st.text_input("q（必填；關鍵字）", "清單測試")
with col4:
    top_k = st.number_input("top_k", min_value=1, max_value=100, value=5, step=1)

if st.button("搜尋"):
    try:
        resp = requests.get(
            f"{base_url}/memory/search",
            headers=headers,
            params={"q": q, "top_k": int(top_k)},
            timeout=30
        )
        # 原始結果
        st.caption("原始回應：")
        st.code(resp.text, language="json")

        if resp.ok:
            data = resp.json()
            hits = data.get("results") or []
            st.success(f"✅ 命中 {len(hits)} 筆")
            if hits:
                # 以表格顯示
                st.caption("命中列表（表格）：")
                # 安全提取欄位
                table = [
                    {
                        "id": h.get("id"),
                        "content": h.get("content"),
                        "tags": ",".join((h.get("tags") or [])),
                        "ts": h.get("ts"),
                    }
                    for h in hits
                ]
                try:
                    import pandas as pd
                    st.dataframe(pd.DataFrame(table), use_container_width=True)
                except Exception:
                    # 若無 pandas 亦能顯示 JSON
                    st.json(table)
        else:
            st.error(f"❌ 搜尋失敗：HTTP {resp.status_code}")
    except Exception as e:
        st.error(f"請求例外：{e}")

    # 對應的 cURL（可複製）
    curl = (
        'curl -G "{u}/memory/search" \\\n'
        '{tok}'
        '  --data-urlencode "q={q}" \\\n'
        '  --data-urlencode "top_k={k}"'
    ).format(
        u=base_url.rstrip("/"),
        tok=('  -H "X-Auth-Token: {t}" \\\n'.format(t=token) if token else ""),
        q=q, k=int(top_k)
    )
    st.caption("重現同請求（cURL）：")
    st.code(curl, language="bash")

st.divider()

# === 健康檢查 & 路由觀察 ===
st.subheader("🩺 健康檢查 / 路由觀察")
cols = st.columns(3)
with cols[0]:
    if st.button("檢查 /health"):
        try:
            r = requests.get(f"{base_url}/health", timeout=15)
            st.code(r.text, language="json")
        except Exception as e:
            st.error(f"/health 失敗：{e}")
with cols[1]:
    if st.button("查看 /"):
        try:
            r = requests.get(f"{base_url}/", timeout=15)
            st.code(r.text, language="json")
        except Exception as e:
            st.error(f"/ 失敗：{e}")
with cols[2]:
    if st.button("查看 /routes"):
        try:
            r = requests.get(f"{base_url}/routes", timeout=15)
            st.code(r.text, language="json")
        except Exception as e:
            st.error(f"/routes 失敗：{e}")