import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from urllib.parse import urlparse, urljoin
import time

# --- 1. 基本設定・看板表示 ---
st.set_page_config(page_title="🛡️ Web構造比較診断", layout="wide")

st.markdown("""
### 🛡️ Web構造比較診断
**【概要】** 本ツールは、自社と競合のWebサイトを「物理構造」と「コンテンツ内容」の両面から比較し、4つのステップで実務的な改善案を抽出します。  
**【免責事項】** 本診断は生成AIによる診断です。推測、不正確な情報を含む可能性がありますので、一次診断用として参考に使用ください。
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

# --- 2. 物理構造解析関数 ---
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
        "body_preview": soup.get_text()[:1000]
    }

# --- 3. メインUI ---
col_u1, col_u2, col_u3 = st.columns(3)
with col_u1: my_url = st.text_input("自社URL", key="my_url")
with col_u2: comp1_url = st.text_input("競合A", key="c1_url")
with col_u3: comp2_url = st.text_input("競合B (任意)", key="c2_url")

# STEP 1: 業界判定・メタ表示
if st.button("STEP 1：業界を判定"):
    if not my_url or not comp1_url:
        st.warning("自社と競合AのURLを入力してください。")
    else:
        with st.spinner("サイトをスキャン中..."):
            st.session_state.my_data = analyze_site_physics(my_url)
            st.session_state.c1_data = analyze_site_physics(comp1_url)
            st.session_state.c2_data = analyze_site_physics(comp2_url) if comp2_url else None
            
            if "error" in st.session_state.my_data or "error" in st.session_state.c1_data:
                st.error("解析エラー。URLが正しいか、アクセス制限がないか確認してください。")
            else:
                p1 = f"業界名を単語1つで回答せよ。タイトル:{st.session_state.my_data['title']} 内容:{st.session_state.my_data['desc']}"
                st.session_state.industry = model.generate_content(p1).text.strip()
                st.session_state.step = 2

if st.session_state.step >= 2:
    st.divider()
    # 判定根拠（メタディスクリプション）の明示
    st.write("**【判定の根拠となったメタデータ】**")
    st.write(f"・自社：{st.session_state.my_data['desc']}")
    st.write(f"・競合A：{st.session_state.c1_data['desc']}")
    
    # 業界名の修正機能
    st.session_state.industry = st.text_input("業界名（修正が必要な場合は書き換えてください）", st.session_state.industry)
    
    if st.button("診断レポートを一括生成"):
        with st.spinner("レポートを構成中..."):
            def get_stat_text(d):
                if not d or "error" in d: return "取得不可"
                return f"タイトル:{d['title']}, h1:{d['h1']}, h2:{d['h2']}, 内部リンク:{d['internal_links_count']}, 資産:{d['asset_counts']}, プレビュー:{d['body_preview'][:500]}"
            
            c2_info = get_stat_text(st.session_state.c2_data) if st.session_state.c2_data else "なし"
            
            prompt_main = f"""
            Webコンサルタントとして、問い合わせ（CV）最大化のための改善レポートを作成してください。
            業界: {st.session_state.industry}

            【STEP 2：調査レポート】
            Markdownの比較表を作成せよ。以下の3つの小見出しで分けること。
            ・サイト基本情報 (タイトル, H1数)
            ・タグ・リンク構造 (H2数, 内部リンク数)
            ・主要コンテンツ資産 (事例数, ブログ数, 料金ページ, 会社情報数, 問い合わせ導線数)
            表の直下に「※数値はサイト内30〜50ページを巡回した推測値です」と必ず記載せよ。

            【STEP 3：診断レポート】
            1. EEAT診断 (経験・専門性/権威性/信頼性)
            2. SEO / LLMO診断 (構造の明快さ/情報の網羅性とリンク構造/キーワードの接点と継続性)
            3. その他 (CTA・可読性)
            各小見出しの記述は、ラベル（事実、リスク等）を使わず、以下の「4つのブロック（改行）」で構成せよ。
            ・第1段：自社と競合の数値比較（事実）
            ・第2段：それによって何が不足しているか（物理的な欠落）
            ・第3段：(リスク・要チェック)
            ・第4段：ユーザーがどう迷い、問い合わせをせずに離脱するか（問い合わせ機会損失の影響）

            【STEP 4：提言レポート】
            導入文：「これまでの調査・診断に基づき、以下の改善提言を行います。」の1文のみ。
            1. サマリー
               - 1. 診断結果のまとめ：数値差が招いている最大の構造的弱点を整理。
               - 2. 提案の骨子：問い合わせを最大化させるための改修方針を文章で記述。
            2. 優先度別提言（最優先/優先/次の課題）
               各提言に必ず「（最初の一歩）」を入れ、具体的タスクを明示。
               業界キーワード（例：{st.session_state.industry}関連用語）を具体的に引用。
            3. 受注率を高める新コンテンツ案 3案

            自社データ: {get_stat_text(st.session_state.my_data)}
            競合Aデータ: {get_stat_text(st.session_state.c1_data)}
            競合Bデータ: {c2_info}
            """
            st.session_state.full_report = model.generate_content(prompt_main).text
            st.session_state.step = 3

    if 'full_report' in st.session_state:
        st.markdown(st.session_state.full_report)
