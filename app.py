import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from openai import OpenAI
from urllib.parse import urlparse, urljoin

# --- 1. 画面基本設定 ---
st.set_page_config(page_title="🛡️ 戦略Web診断：構造と実務", layout="wide")
st.title("🛡️ 経営戦略型・Web構造比較診断")
st.caption("物理数値の格差から、サイトの『構造的欠陥』を特定し、現場への具体的命令を生成します。")

# --- API設定 ---
try:
    api_key = st.secrets["OPENAI_API_KEY"].strip().strip('"')
    client = OpenAI(api_key=api_key)
except:
    st.error("APIキー（OPENAI_API_KEY）をStreamlitのSecretsに設定してください。")
    st.stop()

# --- 2. 物理構造・解析関数 ---
def get_detailed_metrics(url):
    """
    プログラムによる物理数値の実測。AIに頼らず正確な数値を抽出。
    """
    try:
        url = url.strip()
        if not url.startswith("http"): url = "https://" + url
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
        
        # 1. トップページの解析
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, "html.parser")
        domain = urlparse(url).netloc

        # タグ数集計
        h1_count = len(soup.find_all('h1'))
        h2_count = len(soup.find_all('h2'))
        all_links = soup.find_all('a', href=True)
        internal_links = [l['href'] for l in all_links if domain in urljoin(url, l['href'])]
        
        # サイトマップ確認（存在確認のみ優先）
        sitemap_url = urljoin(url, "/sitemap.xml")
        try:
            has_sitemap = "あり" if requests.get(sitemap_url, timeout=5).status_code == 200 else "なし"
        except:
            has_sitemap = "なし（確認不可）"

        # 2. 資産構成の推測用データ（URLリスト抜粋）
        all_path_list = [urljoin(url, l['href']) for l in all_links[:50]]
        
        text_for_ai = soup.get_text()[:4000] # AIに渡すテキスト抜粋

        return {
            "h1": h1_count, "h2": h2_count, "links": len(internal_links),
            "sitemap": has_sitemap, "url_list": all_path_list,
            "text": text_for_ai, "title": soup.title.string if soup.title else "No Title"
        }
    except Exception as e:
        return f"Error: {str(e)}"

# --- 3. UIセクション ---
st.divider()
st.subheader("🔍 解析対象の設定")
col_u1, col_u2, col_u3 = st.columns(3)

with col_u1:
    my_url = st.text_input("自社URL", placeholder="https://example.com")
with col_u2:
    comp1_url = st.text_input("競合A", placeholder="https://competitor-a.com")
with col_u3:
    comp2_url = st.text_input("競合B（任意）", placeholder="https://competitor-b.com")

if 'step' not in st.session_state: st.session_state.step = 1

# AI生成コメントの定義
ai_disclaimer = "> ※本レポートは生成AIによって作成されたものであり、内容の正確性については必ず人間が最終確認を行ってください。\n\n"

# --- STEP 1: 業界判定 ---
if st.button("STEP 1: 業界を解析") or st.session_state.step > 1:
    if not my_url or not comp1_url:
        st.error("自社URLと競合AのURLは必須です。")
    else:
        with st.spinner("業界判定中..."):
            ind_prompt = f"Webサイトの内容から業界名を1語で回答せよ。例：歯科、法律、不動産\nURL: {my_url}"
            res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": ind_prompt}])
            st.session_state.industry = res.choices[0].message.content.strip()
            st.session_state.step = 2

# --- STEP 2: 調査レポート ---
if st.session_state.step >= 2:
    st.divider()
    industry = st.text_input("解析業界ベース", value=st.session_state.industry)
    
    if st.button("STEP 2: サイト調査レポート生成"):
        with st.spinner("物理構造を計測中..."):
            st.session_state.my_m = get_detailed_metrics(my_url)
            st.session_state.c1_m = get_detailed_metrics(comp1_url)
            st.session_state.c2_m = get_detailed_metrics(comp2_url) if comp2_url else None
            
            def build_stats(d, label):
                if isinstance(d, str): return f"{label}: 解析エラー"
                return f"""
                【{label} 物理数値】
                - title: {d['title']}
                - h1数: {d['h1']} / h2数: {d['h2']}
                - 内部リンク数: {d['links']}
                - サイトマップ: {d['sitemap']}
                - URLリスト(抜粋): {", ".join(d['url_list'][:10])}
                - コンテンツ抜粋: {d['text'][:1000]}
                """
            
            stats_context = build_stats(st.session_state.my_m, "自社") + build_stats(st.session_state.c1_m, "競合A")
            if st.session_state.c2_m: stats_context += build_stats(st.session_state.c2_m, "競合B")

            sys_msg = f"あなたは{industry}業界のWebアナリストです。ですます調で調査レポートを作成してください。提言は含めず、事実のみを記載せよ。"
            user_msg = f"""
            {ai_disclaimer}
            以下の統計データに基づき、調査レポートを作成してください。

            1. 物理構造スペック比較表（Markdown Table）
            - 項目: title / h1 / h2数 / 内部リンク数 / sitemap有無 / ページ種別数（事例・ブログ・料金・会社情報・問い合わせ）
            2. 自社サイトの現状分析
            - 項目: 事業概要、主なページ名、強調分野、実績/事例/料金の有無、導線の特徴
            3. 競合との差分サマリー

            データ:
            {stats_context}
            """
            res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}])
            st.session_state.survey_report = ai_disclaimer + res.choices[0].message.content + f"\n\n{ai_disclaimer}"
            st.session_state.step = 3

    if 'survey_report' in st.session_state:
        st.markdown(st.session_state.survey_report)

# --- STEP 3: 診断レポート ---
if st.session_state.step >= 3:
    if st.button("STEP 3: 診断レポート生成"):
        with st.spinner("論理的診断を実行中..."):
            sys_msg = (
                f"あなたは{st.session_state.industry}業界のWebコンサルタントです。ですます調で回答せよ。\n"
                "【記述ルール：示唆のロジック変更】\n"
                "1. 各項目は「事実：」と「示唆：」に分離せよ。\n"
                "2. 事実の記述：曖昧な表現を禁止し、計測された数値（h2数、サイトマップ有無等）を主語にせよ。\n"
                "3. 示唆の深化：不備が『AI検索（LLMO）での未検出』や『スマホ離脱』にどう直結しているか論理的に記述せよ。"
            )
            user_msg = f"{ai_disclaimer}以下の調査レポートに基づき診断を行え。\n\n調査レポート：\n{st.session_state.survey_report}"
            res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}])
            st.session_state.diag_report = ai_disclaimer + res.choices[0].message.content + f"\n\n{ai_disclaimer}"
            st.session_state.step = 4

    if 'diag_report' in st.session_state:
        st.markdown(st.session_state.diag_report)

# --- STEP 4: 提言レポート ---
if st.session_state.step >= 4:
    if st.button("STEP 4: 提言レポート生成"):
        with st.spinner("実務命令を生成中..."):
            sys_msg = (
                f"あなたは{st.session_state.industry}業界のWebコンサルタントです。\n"
                "【提言ルール】\n"
                "- 企画案は、不足しているページ種別（事例等）を補完する器作りを優先せよ。\n"
                "- アクションプランは【3項目】に厳選し、以下の順序で指示せよ。\n"
                "  1. 物理構造の修復（インフラ：タグ階層、sitemap、リンク）\n"
                "  2. UX・可読性の改善（文字の壁の解体、スマホ導線修正）\n"
                "  3. コンテンツ資産の補完（欠落したページ種別の新設）\n"
                "- [どのページ]の[どの箇所]を[どう書き換えるか]をピンポイントで指示せよ。"
            )
            user_msg = f"{ai_disclaimer}診断レポートに基づき、具体的提言を行え。\n\n診断レポート：\n{st.session_state.diag_report}"
            res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}])
            st.session_state.proposal_report = ai_disclaimer + res.choices[0].message.content + f"\n\n{ai_disclaimer}"

    if 'proposal_report' in st.session_state:
        st.markdown(st.session_state.proposal_report)
