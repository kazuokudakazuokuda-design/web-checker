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
    # 最新モデル Gemini 2.5 Flash を指定
    model = genai.GenerativeModel('models/gemini-2.5-flash')
except Exception as e:
    st.error(f"初期設定エラー: {e}")
    st.stop()

# --- 2. 物理構造解析関数 ---
def analyze_site_physics(url, limit_pages=30):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
    url = url.strip()
    if not url.startswith("http"): url = "https://" + url
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        return {"error": True, "message": str(e)}

    m_desc = soup.find("meta", attrs={"name": "description"})
    h1_count = len(soup.find_all('h1'))
    h2_count = len(soup.find_all('h2'))
    all_links = soup.find_all('a', href=True)
    domain = urlparse(url).netloc
    internal_links = [urljoin(url, l['href']) for l in all_links if domain in urljoin(url, l['href'])]
    
    asset_counts = {"事例": 0, "ブログ": 0, "料金": 0, "会社情報": 0, "問い合わせ": 0}
    for link in list(set(internal_links))[:limit_pages]:
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
        "body_preview": soup.get_text()[:800]
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
                st.error("解析エラー。URLを再確認してください。")
            else:
                p1 = f"業界名を単語1つで回答せよ。タイトル:{st.session_state.my_data['title']} 内容:{st.session_state.my_data['desc']}"
                try:
                    st.session_state.industry = model.generate_content(p1).text.strip()
                    st.session_state.step = 2
                except Exception as e:
                    st.error(f"AI判定エラー: {e}")

if st.session_state.step >= 2:
    st.divider()
    st.write(f"### 業界：{st.session_state.industry}")
    
    if st.button("診断レポートを一括生成"):
        with st.spinner("レポート生成中..."):
            def get_stat_text(d):
                if not d or "error" in d: return "データなし"
                return f"タイトル:{d['title']}, h1:{d['h1']}, h2:{d['h2']}, 内部リンク:{d['internal_links_count']}, 資産:{d['asset_counts']}, 冒頭:{d['body_preview']}"
            
            c2_info = get_stat_text(st.session_state.c2_data) if st.session_state.c2_data else "なし"
            
            prompt_main = f"""
            Webコンサルタントとして、問い合わせ（CV）最大化のためのレポートを作成してください。
            
            【構成ルール】
            1. 「経営」等の推測は避け、「サイト上の情報の欠落」と「問い合わせ機会損失」の事実に徹すること。
            2. 「○○分野」等の伏せ字禁止。具体的キーワード（相続、離婚、労働等）を引用。引用不可なら「具体的に、こんな分野、やテーマなどを、」と記述。
            
            【レポート項目】
            ・STEP 2：調査レポート（スペック比較表）
            ・STEP 3：診断レポート
               - 1.EEAT診断(経験・専門性/権威性/信頼性)
               - 2.SEO/LLMO診断(構造の明快さ/網羅性とリンク/接点と継続性)
               - 3.その他
               形式：「自社〇件対競合〇件(事実)→〇〇の不足(物理)→(リスク・要チェック)→ユーザーが〇〇で迷い問い合わせず離脱(影響)」
            ・STEP 4：提言レポート
               導入文：「これまでの調査・診断に基づき、以下の改善提言を行います。」
               サマリー：1.診断結果のまとめ（阻害要因）, 2.提案の骨子（問い合わせ最大化方針）
               優先度別提言：最優先/優先/次の課題（それぞれに「（最初の一歩）」を含む）
               受注率（問い合わせ率）を高める新コンテンツ案 3案

            自社データ: {get_stat_text(st.session_state.my_data)}
            競合Aデータ: {get_stat_text(st.session_state.c1_data)}
            競合Bデータ: {c2_info}
            """
            try:
                st.session_state.full_report = model.generate_content(prompt_main).text
                st.session_state.step = 3
            except Exception as e:
                st.error(f"レポート生成エラー: {e}")

    if 'full_report' in st.session_state:
        st.markdown(st.session_state.full_report)
