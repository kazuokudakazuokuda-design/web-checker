import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from urllib.parse import urlparse, urljoin
import time

# --- 1. 基本設定 ---
st.set_page_config(page_title="🛡️ Web構造比較診断", layout="wide")

if 'step' not in st.session_state:
    st.session_state.step = 1

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # モデル名を確実に存在する 'gemini-1.5-flash' に修正
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("APIキーの設定を確認してください。")
    st.stop()

# --- 2. 物理構造解析関数 ---
def analyze_site_physics(url, limit_pages=30):
    for i in range(2):
        try:
            url = url.strip()
            if not url.startswith("http"): url = "https://" + url
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                r.encoding = r.apparent_encoding
                soup = BeautifulSoup(r.text, "html.parser")
                break
            else:
                if i == 0: time.sleep(1); continue
                return {"error": True, "message": f"Status: {r.status_code}"}
        except Exception as e:
            if i == 0: time.sleep(1); continue
            return {"error": True, "message": str(e)}

    m_desc = soup.find("meta", attrs={"name": "description"})
    h1_count = len(soup.find_all('h1'))
    h2_count = len(soup.find_all('h2'))
    all_links = soup.find_all('a', href=True)
    domain = urlparse(url).netloc
    internal_links = [urljoin(url, l['href']) for l in all_links if domain in urljoin(url, l['href'])]
    
    asset_counts = {"事例": 0, "ブログ": 0, "料金": 0, "会社情報": 0, "問い合わせ": 0}
    check_links = list(set(internal_links))[:limit_pages]
    for link in check_links:
        l_lower = link.lower()
        if any(x in l_lower for x in ["case", "jirei", "works", "results"]): asset_counts["事例"] += 1
        if any(x in l_lower for x in ["blog", "column", "news"]): asset_counts["ブログ"] += 1
        if any(x in l_lower for x in ["price", "fee", "hiyo", "ryokin"]): asset_counts["料金"] += 1
        if any(x in l_lower for x in ["about", "company", "office", "access", "profile"]): asset_counts["会社情報"] += 1
        if any(x in l_lower for x in ["contact", "inquiry", "entry", "form"]): asset_counts["問い合わせ"] += 1

    return {
        "title": soup.title.string if soup.title else "No Title",
        "desc": m_desc["content"] if m_desc else "未設定",
        "h1": h1_count, "h2": h2_count, "total_links": len(all_links),
        "internal_links_count": len(internal_links),
        "asset_counts": asset_counts,
        "keywords": soup.get_text()[:1000]
    }

# --- 3. メインUI ---
st.title("🛡️ Web構造比較診断")

col_u1, col_u2, col_u3 = st.columns(3)
with col_u1: my_url = st.text_input("自社URL")
with col_u2: comp1_url = st.text_input("競合A")
with col_u3: comp2_url = st.text_input("競合B (任意)")

if st.button("STEP 1：業界を判定"):
    if not my_url or not comp1_url:
        st.warning("自社と競合AのURLを入力してください。")
    else:
        with st.spinner("解析中..."):
            st.session_state.my_data = analyze_site_physics(my_url)
            st.session_state.c1_data = analyze_site_physics(comp1_url)
            st.session_state.c2_data = analyze_site_physics(comp2_url) if comp2_url else None
            
            if "error" in st.session_state.my_data or "error" in st.session_state.c1_data:
                st.error("解析に失敗しました。URLを確認してください。")
            else:
                prompt_s1 = f"業界名を単語1つで回答せよ。タイトル:{st.session_state.my_data['title']} 内容:{st.session_state.my_data['desc']}"
                st.session_state.industry = model.generate_content(prompt_s1).text.strip()
                st.session_state.step = 2

if st.session_state.step >= 2:
    st.divider()
    st.write(f"### 業界：{st.session_state.industry}")
    
    if st.button("診断レポートを一括生成"):
        with st.spinner("生成中..."):
            def format_stats(d):
                if not d or "error" in d: return "データなし"
                return f"タイトル:{d['title']}, h1:{d['h1']}, h2:{d['h2']}, 全リンク:{d['total_links']}, 内部リンク:{d['internal_links_count']}, 資産:{d['asset_counts']}, 冒頭:{d['keywords'][:500]}"
            
            c2_info = format_stats(st.session_state.c2_data) if st.session_state.c2_data else "なし"
            
            prompt_main = f"""
            プロのWebコンサルタントとして診断レポートを作成してください。
            【厳守ルール】
            1. 「経営戦略」等の外の推測は避け、「情報の欠落」と「問い合わせ機会損失」の事実に徹すること。
            2. 「○○分野」等の伏せ字禁止。解析データからキーワード（相続、離婚、労働等）を引用。引用不可なら「具体的に、こんな分野、やテーマなどを、」と記述。
            3. 構成：
               【STEP 2：調査レポート】スペック比較表（Markdown）
               【STEP 3：診断レポート】
               見出し：1.EEAT診断(経験・専門性/権威性/信頼性), 2.SEO/LLMO診断, 3.その他
               形式：「自社〇件対競合〇件(事実)→〇〇の不足(物理)→(リスク・要チェック)→ユーザーが〇〇で迷い問い合わせず離脱(影響)」
               【STEP 4：提言レポート】
               導入文：「これまでの調査・診断に基づき、以下の改善提言を行います。」
               内容：サマリー(1.まとめ, 2.骨子), 優先度別提言(最初の一歩を含む), 新コンテンツ案3案

            自社:{format_stats(st.session_state.my_data)} / 競合A:{format_stats(st.session_state.c1_data)} / 競合B:{c2_info}
            """
            st.session_state.full_report = model.generate_content(prompt_main).text
            st.session_state.step = 3

    if 'full_report' in st.session_state:
        st.markdown(st.session_state.full_report)
