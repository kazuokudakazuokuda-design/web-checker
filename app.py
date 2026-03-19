import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from urllib.parse import urlparse, urljoin

# --- 1. 基本設定 ---
st.set_page_config(page_title="🛡️ Web構造比較診断", layout="wide")

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
except:
    st.error("エラー：StreamlitのSecretsに 'GEMINI_API_KEY' が設定されていません。")
    st.stop()

# --- 2. 物理構造・統計データ解析関数 ---
def analyze_site_physics(url, limit_pages=50):
    try:
        url = url.strip()
        if not url.startswith("http"): url = "https://" + url
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, "html.parser")

        m_desc = soup.find("meta", attrs={"name": "description"})
        h1_count = len(soup.find_all('h1'))
        h2_count = len(soup.find_all('h2'))
        all_links = soup.find_all('a', href=True)
        domain = urlparse(url).netloc
        internal_links = [urljoin(url, l['href']) for l in all_links if domain in urljoin(url, l['href'])]
        
        sitemap_url = urljoin(url, "/sitemap.xml")
        try:
            has_sitemap = "あり" if requests.head(sitemap_url, timeout=5).status_code == 200 else "なし"
        except:
            has_sitemap = "なし"

        asset_counts = {"事例": 0, "ブログ": 0, "料金": 0, "会社情報": 0, "問い合わせ": 0}
        for link in list(set(internal_links))[:limit_pages]:
            l_lower = link.lower()
            if any(x in l_lower for x in ["case", "jirei", "works"]): asset_counts["事例"] += 1
            if any(x in l_lower for x in ["blog", "column", "news"]): asset_counts["ブログ"] += 1
            if any(x in l_lower for x in ["price", "fee", "hiyo"]): asset_counts["料金"] += 1
            if any(x in l_lower for x in ["about", "company", "office", "access"]): asset_counts["会社情報"] += 1
            if any(x in l_lower for x in ["contact", "inquiry", "entry"]): asset_counts["問い合わせ"] += 1

        return {
            "title": soup.title.string if soup.title else "No Title",
            "desc": m_desc["content"] if m_desc else "未設定",
            "h1": h1_count, "h2": h2_count, "total_links": len(all_links),
            "internal_links_count": len(internal_links),
            "sitemap": has_sitemap,
            "asset_counts": asset_counts,
            "body_text": soup.get_text()[:1500]
        }
    except Exception as e:
        return f"Error: {str(e)}"

# --- 3. メインUI ---
st.title("🛡️ 経営戦略型・Web構造比較診断")

# URL入力セクション
col_u1, col_u2, col_u3 = st.columns(3)
with col_u1: my_url = st.text_input("自社URL")
with col_u2: comp1_url = st.text_input("競合A")
with col_u3: comp2_url = st.text_input("競合B")

# ステップと注意喚起
st.write("---")
st.write("**【概要】** 本ツールは、自社と競合のWebサイトを「物理構造」と「コンテンツ内容」の両面から比較し、4つのステップで実務的な改善案を抽出します。")
st.write("本診断は生成AIによる診断です。推測、不正確な情報を含む可能性がありますので、一次診断用として参考に使用ください。")

if 'step' not in st.session_state: st.session_state.step = 1

# --- STEP 1：業界判定 ---
if st.button("STEP 1：業界を判定"):
    if not my_url or not comp1_url:
        st.warning("診断を開始するには、自社URLと競合AのURLを入力してください。")
    else:
        with st.spinner("メタデータを解析中..."):
            st.session_state.my_data = analyze_site_physics(my_url)
            st.session_state.c1_data = analyze_site_physics(comp1_url)
            st.session_state.c2_data = analyze_site_physics(comp2_url) if comp2_url else None
            
            prompt_s1 = f"URLおよびメタディスクリプションから業界名を1語で特定せよ。\n自社Meta: {st.session_state.my_data['desc']}\n競合AMeta: {st.session_state.c1_data['desc']}"
            st.session_state.industry = model.generate_content(prompt_s1).text.strip()
            st.session_state.step = 2

# STEP 1 判定結果の表示（修正可能・オープン状態）
if st.session_state.step >= 2:
    st.write("---")
    st.subheader("STEP 1：業界の特定")
    
    st.write("AI判定の業界名です。より正確な診断のため、必要に応じて修正してください。")
    st.session_state.industry = st.text_input("業界名", st.session_state.industry)
    st.caption("※ 業界は読み違えたり、大きくまたは小さくとらえることがあるので、適宜修正をたのみます。")

    st.write("### トップページのメタデータ")
    st.write(f"・自社Meta: {st.session_state.my_data['desc']}")
    st.write(f"・競合AMeta: {st.session_state.c1_data['desc']}")
    if st.session_state.c2_data:
        st.write(f"・競合BMeta: {st.session_state.c2_data['desc']}")

    # --- STEP 2：調査レポート ---
    if st.button("STEP 2：調査レポートを生成"):
        with st.spinner("比較レポートを生成中..."):
            def get_stats(d):
                return f"title:{d['title']}, h1:{d['h1']}, h2:{d['h2']}, a:{d['total_links']}, sitemap:{d['sitemap']}, 内部リンク:{d['internal_links_count']}, 資産:{d['asset_counts']}"
            
            c1_info = f"【競合A】{get_stats(st.session_state.c1_data)} / 本文抜粋: {st.session_state.c1_data['body_text']}"
            c2_info = f"\n【競合B】{get_stats(st.session_state.c2_data)} / 本文抜粋: {st.session_state.c2_data['body_text']}" if st.session_state.c2_data else ""
            
            prompt_s2 = f"""
            あなたは{st.session_state.industry}業界の専門調査員です。以下の構成でレポートを作成してください。
            語尾は「です・ます」調で、礼節を保ったプロフェッショナルなトーンを徹底してください。

            1. 調査項目詳細抽出（事業概要、主なページ名、強調分野、実績・事例・料金表・ブログの有無、問い合わせ導線の特徴）
            2. スペック比較表（Markdown Table）
               項目: title / h1 / h2 / a(総リンク) / sitemap.xml / 内部リンク数 / 資産構成（事例/ブログ/料金/会社情報/問い合わせ）
            
            【自社データ】{get_stats(st.session_state.my_data)} / 本文抜粋: {st.session_state.my_data['body_text']}
            {c1_info}{c2_info}
            """
            st.session_state.report_s2 = model.generate_content(prompt_s2).text
            
            # 数値に基づく100文字コメントを生成
            prompt_comm = f"以下のスペック表の数値を見て、自社と競合の決定的な差や改善のヒントを、数値に基づいて100文字以内で礼儀正しくコメントしてください。\n{st.session_state.report_s2}"
            st.session_state.comm_s2 = model.generate_content(prompt_comm).text
            st.session_state.step = 3

    if 'report_s2' in st.session_state:
        # スペック表への注釈挿入
        updated_report = st.session_state.report_s2.replace("スペック比較表", "### スペック比較表\n\n**※本表はサイト内30〜50ページの巡回に基づく推測値です。**")
        st.markdown(updated_report)
        st.info(st.session_state.comm_s2)

    # --- STEP 3：診断レポート ---
    if st.session_state.step >= 3:
        if st.button("STEP 3：診断レポートを生成"):
            with st.spinner("論理診断を実行中..."):
                prompt_s3 = f"""
                以下のレポートに基づき診断を行ってください。
                礼節を保ち、建設的なトーンで、「です・ます」調を徹底してください。

                1. 構成: EEAT診断、SEO / LLMO診断、その他（CTA・可読性）
                2. 記述ロジック:
                   - 「事実：」「示唆：」に分けて記述してください。
                   - 曖昧な表現を避け、数値を主語にしてください。
                   - 構造の不備が「AI検索（LLMO）での未検出」や「スマホユーザーの迷い」にどう直結しているか論理的に記述してください。
                
                レポート原文:
                {st.session_state.report_s2}
                """
                st.session_state.report_s3 = model.generate_content(prompt_s3).text
                st.session_state.step = 4
                
        if 'report_s3' in st.session_state:
            st.markdown(st.session_state.report_s3)

    # --- STEP 4：提言レポート ---
    if st.session_state.step >= 4:
        if st.button("STEP 4：提言レポートを生成"):
            with st.spinner("改善アクションプランを策定中..."):
                prompt_s4 = f"""
                診断に基づき、改善提言を行ってください。
                過激な表現を避け、礼節ある専門家として「です・ます」調で記述してください。

                1. サマリー
                   - 分析結果の要約（200文字程度）
                   - 提言の骨子（なぜその優先順位なのか、根拠を添えて数行で明記）

                2. 優先度別提言
                   - 「最優先」: 直ちに改善が必要な事項。
                   - 「優先」: 競合に追いつき、信頼を構築するための施策。
                   - 「次の課題」: 中長期的な差別化へのステップ。
                   （※見出しに余計な装飾をつけず、診断に基づいた具体的な内容を記述してください）

                3. 新コンテンツ案
                   - 不足している「ページ種別（器作り）」を優先した3案（テーマ、構成）。

                診断内容:
                {st.session_state.report_s3}
                """
                st.session_state.report_s4 = model.generate_content(prompt_s4).text
                
        if 'report_s4' in st.session_state:
            st.markdown(st.session_state.report_s4)
            st.write("---")
            st.write("本診断は生成AIによる診断です。推測、不正確な情報を含む可能性がありますので、一次診断用として参考に使用ください。")
