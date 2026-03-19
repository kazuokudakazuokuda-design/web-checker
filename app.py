import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from urllib.parse import urlparse, urljoin
import time

# --- 1. 基本設定・看板表示 ---
st.set_page_config(page_title="🛡️ Web構造比較診断", layout="wide")

# CSS: 見出しサイズと余白の徹底調整
st.markdown("""
    <style>
    h2 { 
        font-size: 2.2em !important; 
        font-weight: 800 !important; 
        color: #1E1E1E !important;
        border-left: 15px solid #1f77b4;
        padding-left: 20px;
        margin-top: 1.5em !important;
        margin-bottom: 1.0em !important;
        line-height: 1.2 !important;
    }
    h3 { 
        font-size: 1.5em !important; 
        font-weight: bold !important; 
        margin-top: 1.2em !important; 
        color: #2c3e50;
    }
    table { 
        width: 100% !important; 
        table-layout: fixed !important; 
        border-collapse: collapse !important;
    }
    td, th { 
        word-wrap: break-word !important; 
        white-space: normal !important; 
        font-size: 1.1em !important; 
        padding: 12px !important;
        border: 1px solid #ddd !important;
    }
    th { background-color: #f8f9fa !important; }
    </style>
""", unsafe_allow_html=True)

# 看板部分：指示通りの改行と文言
st.markdown("""
# 🛡️ Web構造比較診断

**【概要】** 本ツールは、自社と競合のWebサイトを「物理構造」と「コンテンツ内容」の両面から比較し、4つのステップで実務的な改善案を抽出します。

本診断は生成AIによる診断です。推測、不正確な情報を含む可能性がありますので、一次診断用として参考に使用ください。
""")

if 'step' not in st.session_state:
    st.session_state.step = 1

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-2.5-flash')
except Exception as e:
    st.error(f"初期設定エラー: {e}")
    st.stop()

# --- 2. 解析関数 ---
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
    
    asset_counts = {"事例": 0, "ブログ": 0}
    for link in list(set(internal_links))[:limit_pages]:
        l_lower = link.lower()
        if any(x in l_lower for x in ["case", "jirei", "works", "results"]): asset_counts["事例"] += 1
        if any(x in l_lower for x in ["blog", "column", "news"]): asset_counts["ブログ"] += 1

    return {
        "title": (soup.title.string[:25] + "...") if soup.title and len(soup.title.string) > 25 else (soup.title.string if soup.title else "No Title"),
        "desc": m_desc["content"] if m_desc else "未設定",
        "h1": h1_count, "h2": h2_count, "total_links": len(all_links),
        "internal_links_count": len(internal_links),
        "asset_counts": asset_counts,
        "body_preview": soup.get_text()[:1500] 
    }

# --- 3. UI部 ---
col_u1, col_u2, col_u3 = st.columns(3)
with col_u1: my_url = st.text_input("自社URL", key="my_url_in", placeholder="https://example.com")
with col_u2: comp1_url = st.text_input("競合A", key="c1_url_in", placeholder="https://comp-a.com")
with col_u3: comp2_url = st.text_input("競合B (任意)", key="c2_url_in", placeholder="https://comp-b.com")

if st.button("STEP 1：業界を判定"):
    if not my_url or not comp1_url:
        st.warning("自社と競合AのURLを入力してください。")
    else:
        with st.spinner("スキャン中..."):
            st.session_state.my_data = analyze_site_physics(my_url)
            st.session_state.c1_data = analyze_site_physics(comp1_url)
            st.session_state.c2_data = analyze_site_physics(comp2_url) if comp2_url else None
            
            error_found = False
            for data, url in [(st.session_state.my_data, my_url), (st.session_state.c1_data, comp1_url), (st.session_state.c2_data, comp2_url)]:
                if data and "error" in data:
                    st.error(f"URL：{url} は現在読み込めません。サイト側のセキュリティ対策（WAF等）により、自動解析がブロックされている可能性があります。URLが正しいか確認するか、別の競合サイトでお試しください。")
                    error_found = True
            
            if not error_found:
                p1 = f"業界名を単語1つで回答せよ。タイトル:{st.session_state.my_data['title']} 内容:{st.session_state.my_data['desc']}"
                st.session_state.industry = model.generate_content(p1).text.strip()
                st.session_state.step = 2

if st.session_state.step >= 2:
    st.divider()
    st.session_state.industry = st.text_input("業界名", st.session_state.industry)
    
    st.write("**トップページのメタディスクリプション**")
    st.write(f"・自社：{st.session_state.my_data['desc']}")
    st.write(f"・競合A：{st.session_state.c1_data['desc']}")
    if st.session_state.c2_data:
        st.write(f"・競合B：{st.session_state.c2_data['desc']}")
    
    if st.button("診断レポートを一括生成"):
        with st.spinner("詳細レポートを構築中..."):
            def format_data(d):
                if not d or "error" in d: return "データなし"
                return f"タイトル:{d['title']}, h1:{d['h1']}, h2:{d['h2']}, 内部リンク:{d['internal_links_count']}, 事例:{d['asset_counts']['事例']}, ブログ:{d['asset_counts']['ブログ']}, プレビュー:{d['body_preview']}"
            
            c2_info = format_data(st.session_state.c2_data) if st.session_state.c2_data else "なし"
            
            prompt_main = f"""
            解析結果からレポートを作成せよ。挨拶や前置きは一切不要。
            
            重要ルール：
            ・メタディスクリプションの要約・改変禁止：取得したデータは原文のまま表示・分析に使用し、一字一句変えずに扱うこと。
            ・各見出し（##や###）、各項目（■項目名）、および各段落の間には必ず【空行（1行分の空白）】を挿入せよ。文字を絶対に詰めないこと。

            ## 【STEP 2：調査レポート】

            Markdownで比較表を作成（会社名を行、項目を列に）。
            項目：サイトタイトル, H1数, H2数, 内部リンク, 事例数, ブログ数, 最終更新日
            ※最終更新日はプレビューから推測せよ。不明なら不明で良い。

            ※表の直後には必ず【空行】を入れ、「※数値はサイト内30〜50ページを巡回した推測値です」と必ず記載せよ。

            ## 【STEP 3：診断レポート】

            以下の大項目（##）の中に、必ず指定の小見出し（### ■項目名）をすべて立てて記述せよ。
            各小見出しの直後、および各ブロック（第1段〜第3段）の間には必ず【空行】を挟め。
            
            ※「日付が未来である」等の不確かな指摘はAI側の誤検知リスクがあるため、一切禁止する。
            
            1. EEAT診断
               ### ■経験・専門性
               ### ■権威性
               ### ■信頼性
            2. SEO / LLMO診断
               ### ■構造の明快さ
               ### ■情報の網羅性とリンク構造
               ### ■キーワードの接点と継続性
            3. その他
               ### ■可読性とコンテンツ量
            
            各項目の記述ルール：
            ・第1段：事実と解釈。数値を自然に組み込み、0や低数値は「AIや検索エンジンが見つけにくい状態」と明記。
            ・第2段：(リスク・要チェック) 
            ・第3段：影響。ユーザーがどう迷い問い合わせず離脱するか。

            ## 【STEP 4：提言レポート】

            導入文：「これまでの調査・診断に基づき、以下の改善提言を行います。」のみ。
            
            1. サマリー
               - 1. 診断結果のまとめ（阻害要因を動的に整理）
               - 2. 提案の骨子（問い合わせ最大化方針を文章で記述）
               ※各箇条書きの間には【空行】を入れよ。
            
            2. 優先度別提言（最優先/優先/次の課題）
               ※スペック表の数値差を比較し、AIが動的に選別して優先順位をつけよ。
               【記述ルール】：見出し（【最優先】等）の直後、説明文の直後、（最初の一歩）の直前には、必ず【空行】を挿入せよ。
            
            3. 新コンテンツ３案
               「タイトル」と、制作に役立つ「詳細な構成・内容」のみを提示せよ。
               ※タイトルと構成・内容の間には必ず【空行】を入れよ。

            自社データ: {format_data(st.session_state.my_data)}
            競合Aデータ: {format_data(st.session_state.c1_data)}
            競合Bデータ: {c2_info}
            """
            st.session_state.full_report = model.generate_content(prompt_main).text
            st.session_state.step = 3

    if 'full_report' in st.session_state:
        st.markdown(st.session_state.full_report)
