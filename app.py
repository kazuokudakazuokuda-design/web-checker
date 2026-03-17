import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import streamlit.components.v1 as components

# 1. 画面構成
st.set_page_config(page_title="🛡️ 業界特化型 Web戦略診断", layout="wide")
st.title("🛡️ 業界特化型 Web戦略診断")
st.caption("※あくまで生成AIによる一次診断としてご利用ください。情報が不確かな場合があります。")

# Secrets
try:
    api_key = st.secrets["OPENAI_API_KEY"].strip().strip('"')
    client = OpenAI(api_key=api_key)
except:
    st.error("APIキーの設定を確認してください。")
    st.stop()

def get_site_content(url):
    try:
        url = url.strip()
        if not url.startswith("http"): url = "https://" + url
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Meta Descriptionの取得
        meta_desc = soup.find("meta", attrs={"name": "description"})
        description = meta_desc["content"].strip() if meta_desc else "設定なし"
        
        # 本文テキストの抽出
        for s in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            s.decompose()
        lines = []
        for tag in soup.find_all(['title', 'h1', 'h2', 'h3', 'h4', 'p', 'li', 'dt', 'dd', 'table']):
            text = tag.get_text().strip()
            if len(text) > 2:
                lines.append(f"<{tag.name}>{text}")
        content = "\n".join(lines)[:8000]
        
        return {"description": description, "content": content}
    except Exception as e:
        return {"description": "取得エラー", "content": "データ取得エラー"}

# レポート一括コピー用JavaScript
def copy_to_clipboard_js(text):
    escaped_text = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    js_code = f"""
    <script>
    function copyText() {{
        const text = `{escaped_text}`;
        navigator.clipboard.writeText(text).then(() => {{
            alert("レポートをコピーしました！");
        }});
    }}
    </script>
    <button onclick="copyText()" style="
        background-color: #ff4b4b; color: white; border: none; padding: 10px 20px;
        border-radius: 5px; cursor: pointer; font-weight: bold; width: 100%; margin-bottom: 20px;
    ">📋 レポートをコピーする（Markdown形式）</button>
    """
    return components.html(js_code, height=70)

if 'step' not in st.session_state:
    st.session_state.step = 1
    st.session_state.industry = ""
    st.session_state.full_report = ""

with st.sidebar:
    st.header("🔍 解析対象設定")
    my_url = st.text_input("自社URL", placeholder="https://example.com")
    comp1_url = st.text_input("競合A", placeholder="https://competitor-a.com")
    comp2_url = st.text_input("競合B", placeholder="（任意）")
    if st.button("STEP 1: 業界を特定する"):
        if not my_url or not comp1_url:
            st.error("自社と競合AのURLは必須です。")
        else:
            with st.spinner("業界を解析中..."):
                st.session_state.my_res = get_site_content(my_url)
                st.session_state.c1_res = get_site_content(comp1_url)
                st.session_state.c2_res = get_site_content(comp2_url) if comp2_url else {"description": "なし", "content": "なし"}
                st.session_state.urls = {"my": my_url, "c1": comp1_url, "c2": comp2_url if comp2_url else "-"}
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": f"業界名を回答せよ。余計な言葉は不要。\n\n自社:{st.session_state.my_res['
