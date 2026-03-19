import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from urllib.parse import urlparse, urljoin
import time

# --- 1. 基本設定・看板表示 [cite: 77, 78] ---
st.set_page_config(page_title="🛡️ Web構造比較診断", layout="wide")

st.markdown("""
### 🛡️ Web構造比較診断
**【概要】** 本ツールは、自社と競合のWebサイトを「物理構造」と「コンテンツ内容」の両面から比較し、4つのステップで実務的な改善案を抽出します [cite: 77]。  
**【免責事項】** 本診断は生成AIによる診断です。推測、不正確な情報を含む可能性がありますので、一次診断用として参考に使用ください [cite: 78]。
""")

if 'step' not in st.session_state:
    st.session_state.step = 1

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 最新の Gemini 2.5 Flash モデルを指定
    model = genai.GenerativeModel('models/gemini-2.5-flash')
except Exception as e:
    st.error(f"初期設定エラー: {e}")
    st.stop()

# --- 2. 物理構造解析関数 [cite: 97] ---
def analyze_site_physics(url, limit_pages=40):
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
    
    asset_counts = {"事例": 0, "ブログ": 0, "料金": 0, "会社情報": 0, "FAQ": 0, "導線": 0}
    # 30-50ページを巡回 [cite: 97]
    for link in list(set(internal_links))[:limit_pages]:
        l_lower = link.lower()
        if any(x in l_lower for x in ["case", "jirei", "works", "results"]): asset_counts["事例"] += 1
        if any(x in l_lower for x in ["blog", "column", "news"]): asset_counts["ブログ"] += 1
        if any(x in l_lower for x in ["price", "fee", "hiyo", "ryokin"]): asset_counts["料金"] += 1
        if any(x in l_lower for x in ["about", "company", "office", "access", "profile"]): asset_counts["会社情報"] += 1
        if any(x in l_lower for x in ["faq", "qa", "question"]): asset_counts["FAQ"] += 1
        if any(x in l_lower for x in ["contact", "inquiry", "entry", "form", "reserve", "line"]): asset_counts["導線"] += 1

    return {
        "title": (soup.title.string[:20] + "...") if soup.title and len(soup.title.string) > 20 else (soup.title.string if soup.title else "No Title"),
        "desc": m_desc["content"] if m_desc else "未設定",
        "h1": h1_count, "h2": h2_count, "total_links": len(all_links),
        "internal_links_count": len(internal_links),
        "asset_counts": asset_counts,
        "body_preview": soup.get_text()[:800]
    }

# --- 3. メインUI ---
col_u1, col_u2, col_u3 = st.columns(3)
with col_u1: my_url = st.text_input("自社URL", key="my_url") # [cite: 80]
with col_u2: comp1_url = st.text_input("競合A", key="c1_url") # [cite: 84]
with col_u3: comp2_url = st.text_input("競合B (任意)", key="c2_url") # [cite: 85]

# STEP 1: 業界判定
if st.button("STEP 1：業界を判定"): # [cite: 81]
    if not my_url or not comp1_url:
        st.warning("自社と競合AのURLを入力してください。")
    else:
        with st.spinner("サイトをスキャン中..."):
            st.session_state.my_data = analyze_site_physics(my_url)
            st.session_state.c1_data = analyze_site_physics(comp1_url)
            st.session_state.c2_data = analyze_site_physics(comp2_url) if comp2_url else None
            
            if "error" in st.session_state.my_data or "error" in st.session_state.c1_data:
                st.error("解析エラー。URLを確認してください。")
            else:
                p1 = f"業界名を単語1つで回答せよ。タイトル:{st.session_state.my_data['title']} 内容:{st.session_state.my_data['desc']}"
                st.session_state.industry = model.generate_content(p1).text.strip() # [cite: 90]
                st.session_state.step = 2

if st.session_state.step >= 2:
    st.divider()
    # 業界名の修正機能 [cite: 89]
    st.session_state.industry = st.text_input("業界名（修正が必要な場合は書き換えてください）", st.session_state.industry)
    
    # トップページのメタディスクリプション表示 [cite: 86-88]
    st.write("**トップページのメタディスクリプション**")
    st.write(f"・自社：{st.session_state.my_data['desc']}")
    st.write(f"・競合A：{st.session_state.c1_data['desc']}")
    
    if st.button("診断レポートを一括生成"): # [cite: 91]
        with st.spinner("レポート生成中..."):
            def get_stat_text(d):
                if not d or "error" in d: return "データなし"
                return f"タイトル:{d['title']}, h1:{d['h1']}, h2:{d['h2']}, 内部リンク:{d['internal_links_count']}, 資産:{d['asset_counts']}, プレビュー:{d['body_preview']}"
            
            c2_info = get_stat_text(st.session_state.c2_data) if st.session_state.c2_data else "なし"
            
            prompt_main = f"""
            Webコンサルタントとして、問い合わせ（CV）最大化のためのレポートを作成してください [cite: 92, 93]。
            【STEP 2：調査レポート】 [cite: 94]
            Markdownで1つの比較表を作成せよ。会社名が行、項目が列となるようにし、横スクロールが発生しないよう項目名を短縮せよ。
            項目：タイトル, H1, H2, 内部リンク, 事例, ブログ, 料金, 会社情報, FAQ, 導線
            表の直下に「※数値はサイト内30〜50ページを巡回した推測値です」と記載せよ [cite: 97]。

            【STEP 3：診断レポート】 [cite: 98]
            以下の見出しと、小見出しを用いて記述せよ。
            1. EEAT診断（経験・専門性 / 権威性 / 信頼性） [cite: 99]
            2. SEO / LLMO診断（構造の明快さ / 情報の網羅性とリンク構造 / キーワードの接点と継続性） [cite: 103]
            3. その他（CTA・可読性） [cite: 107]
            
            記述形式：各小見出しの下で、以下の4つのブロック（改行）で構成せよ。ラベルは不要。
            ・第1段：事実（自社〇件対競合〇件）
            ・第2段：物理的不足（0や低数値は「AIや検索エンジンが見つけにくい構造」と解釈せよ）
            ・第3段：(リスク・要チェック)
            ・第4段：影響（ユーザーがどう迷い問い合わせず離脱するか）

            【STEP 4：提言レポート】 [cite: 111]
            導入文：「これまでの調査・診断に基づき、以下の改善提言を行います。」 [cite: 112]
            1. サマリー [cite: 113]
               - 1. 診断結果のまとめ（阻害要因） [cite: 114]
               - 2. 提案の骨子（問い合わせ最大化方針を文章で） [cite: 115]
            2. 優先度別提言（最優先/優先/次の課題） [cite: 116, 117, 122, 125]
               各提言に必ず「（最初の一歩）」を入れ、具体的タスクを明示 [cite: 118, 123, 126]。解析キーワードを引用せよ。
            3. 受注率を高める新コンテンツ案 3案 [cite: 128, 129, 130, 131]

            自社:{get_stat_text(st.session_state.my_data)} / 競合A:{get_stat_text(st.session_state.c1_data)} / 競合B:{c2_info}
            """
            st.session_state.full_report = model.generate_content(prompt_main).text
            st.session_state.step = 3

    if 'full_report' in st.session_state:
        # 表がスクロールしないよう、CSSでテーブル幅を調整
        st.markdown("<style>table {width: 100% !important; display: table !important; table-layout: fixed !important;} td, th {word-wrap: break-word !important; white-space: normal !important;}</style>", unsafe_allow_html=True)
        st.markdown(st.session_state.full_report)
