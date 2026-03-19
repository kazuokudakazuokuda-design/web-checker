import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from urllib.parse import urlparse, urljoin
import time

# --- 1. 基本設定 ---
st.set_page_config(page_title="🛡️ Web構造比較診断", layout="wide")

# セッション状態の初期化
if 'step' not in st.session_state:
    st.session_state.step = 1

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 最新のモデルを指定
    model = genai.GenerativeModel('gemini-1.5-pro')
except Exception as e:
    st.error("エラー：APIキーの設定を確認してください。")
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

    # 解析処理
    m_desc = soup.find("meta", attrs={"name": "description"})
    h1_count = len(soup.find_all('h1'))
    h2_count = len(soup.find_all('h2'))
    all_links = soup.find_all('a', href=True)
    domain = urlparse(url).netloc
    internal_links = [urljoin(url, l['href']) for l in all_links if domain in urljoin(url, l['href'])]
    
    # コンテンツ資産の簡易カウント
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
        "keywords": soup.get_text()[:1000] # キーワード抽出用
    }

# --- 3. メインUI ---
st.title("🛡️ Web構造比較診断")

col_u1, col_u2, col_u3 = st.columns(3)
with col_u1: my_url = st.text_input("自社URL", placeholder="https://example.com")
with col_u2: comp1_url = st.text_input("競合A", placeholder="https://competitor-a.com")
with col_u3: comp2_url = st.text_input("競合B (任意)", placeholder="https://competitor-b.com")

# --- STEP 1：業界判定 ---
if st.button("STEP 1：業界を判定"):
    if not my_url or not comp1_url:
        st.warning("自社URLと競合AのURLは必須入力です。")
    else:
        with st.spinner("サイト構造を解析中..."):
            st.session_state.my_data = analyze_site_physics(my_url)
            st.session_state.c1_data = analyze_site_physics(comp1_url)
            st.session_state.c2_data = analyze_site_physics(comp2_url) if comp2_url else None
            
            if "error" in st.session_state.my_data or "error" in st.session_state.c1_data:
                st.error("URL解析に失敗しました。接続設定を確認してください。")
            else:
                prompt_s1 = f"""
                以下のサイト内容から、このサイトが属する「業界名」を単語1つで回答せよ。
                自社タイトル: {st.session_state.my_data['title']}
                自社Meta: {st.session_state.my_data['desc']}
                """
                st.session_state.industry = model.generate_content(prompt_s1).text.strip()
                st.session_state.step = 2

if st.session_state.step >= 2:
    st.divider()
    st.write(f"### 判定された業界：{st.session_state.industry}")
    
    if st.button("診断レポートを一括生成"):
        with st.spinner("診断レポートを構築中..."):
            def format_stats(d):
                if not d or "error" in d: return "取得不可"
                return f"タイトル:{d['title']}, h1:{d['h1']}, h2:{d['h2']}, 全リンク:{d['total_links']}, 内部リンク:{d['internal_links_count']}, 資産数:{d['asset_counts']}, 冒頭テキスト:{d['keywords'][:500]}"
            
            c2_info = format_stats(st.session_state.c2_data) if st.session_state.c2_data else "なし"
            
            prompt_main = f"""
            あなたはプロのWebコンサルタントです。以下の解析数値を元に、実務的な診断レポートを作成してください。
            
            【厳守ルール】
            1. 比喩表現や「経営戦略」等のサイト外の推測は排除し、「サイト上の情報の欠落」と「ユーザーの離脱・問い合わせ機会損失」という事実に徹すること。
            2. 「○○分野」等の伏せ字は禁止。解析データから具体的なキーワード（例：相続、離婚、労働など）を引用すること。引用不可な場合のみ「具体的に、こんな分野、やテーマなどを、」と記述すること。
            3. ステップ構成と見出しを以下の通り固定すること。

            ---
            【STEP 2：調査レポート】
            自社・競合A・競合B（あれば）の数値を横並びにしたMarkdown形式のスペック比較表を作成せよ。
            （項目：タイトル, h1数, h2数, 内部リンク数, 事例数, ブログ数, 料金ページ, 会社情報数, 問い合わせページ）

            【STEP 3：診断レポート】
            以下の見出しと構成で記述せよ。各項目の記述は「自社〇件に対し競合〇件（事実）→ 〇〇の不足（物理）→ （リスク・要チェック） → ユーザーが〇〇で迷い、問い合わせに至らず離脱する（影響）」の4段構成を徹底すること。
            
            1. EEAT診断
               - 経験・専門性
               - 権威性
               - 信頼性
            2. SEO / LLMO診断
               - 構造の明快さ
               - 情報の網羅性とリンク構造
               - キーワードの接点と継続性
            3. その他（CTA・可読性）
               - 導線の完備
               - 窓口の多様性

            【STEP 4：提言レポート】
            導入文：「これまでの調査・診断に基づき、以下の改善提言を行います。」
            
            1. サマリー
               - 1. 診断結果のまとめ（数値差が招いている最大の構造的弱点）
               - 2. 提案の骨子（問い合わせを最大化させるための改修方針）
            
            2. 優先度別提言（最優先/優先/次の課題）
               各項目に必ず「（最初の一歩）」を入れ、具体的な着手タスクを明示すること。
            
            3. 受注率を高める新コンテンツ 3案
               問い合わせ（成果）に直結する具体的なページ案を3つ提示せよ。
            ---

            自社データ: {format_stats(st.session_state.my_data)}
            競合Aデータ: {format_stats(st.session_state.c1_data)}
            競合Bデータ: {c2_info}
            """
            st.session_state.full_report = model.generate_content(prompt_main).text
            st.session_state.step = 3

    if 'full_report' in st.session_state:
        st.markdown(st.session_state.full_report)
