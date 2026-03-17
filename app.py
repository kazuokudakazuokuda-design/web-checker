import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# 1. 画面構成とAPIキーの設定
st.set_page_config(page_title="🛡️ AI戦略・実務診断レポート", layout="wide")
st.title("🛡️ プロフェッショナルWeb戦略診断")
st.caption("AIが業界の成功法則を解読し、競合との格差を徹底診断します")

# サイドバーでAPIキーを入力
with st.sidebar:
    st.header("設定")
    api_key = st.text_input("OpenAI API Keyを入力してください", type="password")

if not api_key:
    st.warning("サイドバーにOpenAIのAPIキーを入力してください。")
    st.stop()

client = OpenAI(api_key=api_key)

def get_site_content(url):
    """サイトの文字情報を拾ってくる関数"""
    try:
        url = url.strip()
        if not url.startswith("http"): url = "https://" + url
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, "html.parser")
        for s in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            s.decompose()
        elements = soup.find_all(["title", "h1", "h2", "h3", "p", "li"])
        return "\n".join([e.get_text().strip() for e in elements if e.get_text().strip()])[:8000]
    except Exception as e:
        return f"取得失敗: {str(e)}"

# 2. URLの入力フォーム
with st.form("input_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        my_url = st.text_input("自社サイトURL", placeholder="https://example.com")
    with col2:
        comp1_url = st.text_input("競合サイトA URL", placeholder="https://comp-a.com")
    with col3:
        comp2_url = st.text_input("競合サイトB URL", placeholder="https://comp-b.com")
    
    submit_btn = st.form_submit_button("業界解読・診断開始")

if submit_btn and my_url and comp1_url and comp2_url:
    # データの取得
    with st.spinner("サイト群から「業界の成功法則」を抽出中..."):
        my_data = get_site_content(my_url)
        c1_data = get_site_content(comp1_url)
        c2_data = get_site_content(comp2_url)

    # --- PHASE 1: AIによる業界基準の自動生成 ---
    phase1_prompt = f"""
    以下のサイト情報を分析し、この業界のWeb戦略における「5つの絶対基準」を定義してください。
    自社: {my_data[:1500]} / 競合A: {c1_data[:1500]} / 競合B: {c2_data[:1500]}

    出力形式：
    ■この業界におけるWebサイト5大戦略基準
    1. [基準名]
       - （理由）: [なぜ重要か]
       - （具体的な評価ポイント）: [プロがチェックする具体的な3つの要素]
    """

    res_phase1 = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": phase1_prompt}],
        temperature=0.0
    )
    industry_standards = res_phase1.choices[0].message.content
    
    st.success("STEP 1: 業界基準が定義されました")
    st.markdown(industry_standards)

    st.divider()

    # --- PHASE 2: 詳細レポート生成 ---
    with st.spinner("プロレベルの詳細レポートを生成中（1分程度かかります）..."):
        phase2_prompt = f"""
        あなたは、業界基準と最新のSEO/LLMO（AI検索最適化）を熟知した、一切の妥協を許さないシニアコンサルタントです。
        定義された業界基準に基づき、自社サイトを競合と比較して「徹底的に、具体的に」診断してください。

        【業界基準】:
        {industry_standards}

        【解析対象データ】
        自社: {my_data} / 競合A: {c1_data} / 競合B: {c2_data}

        以下の構成で、具体例を交えて重厚に出力してください：

        ■0. ポジショニング分析
        ・（特徴）: 自社サイトが現在持っている強みやポジショニング。
        ・（競合比較）: 競合A/Bと比較した際の、情報量・UI・信頼感の決定的な差。
        ・（総合評価）: 市場における現在のWeb戦闘力の判定。

        ■1. コンテンツの「網羅性と深さ」
        ・論点：【Q&Aの専門性】【解決事例の一次情報量】【独自の見解/専門コラムの鮮度】
        ・具体的指摘：競合と比較して、自社のどの記述が「浅い」か、何を追加すべきか。

        ■2. 成約導線と「心理的ハードル」
        ・論点：【ファーストビューの3秒ルール】【料金・プロセスの透明性】【信頼感を醸成する非言語情報（写真等）】
        ・具体的指摘：現在のバナー、写真、コピーのどこが「離脱」を招いているか。

        ■3. EEAT（経験・専門性・権威性・信頼性）の診断
        ・論点：【著者の記名性とプロフィールの厚み】【公的・外部データへのリンク】【解決実績の客観的証明】
        ・具体的指摘：GoogleやAIに「専門家」と認めさせるために足りない具体的要素。

        ■4. SEO / LLMO（AI検索）適応状況
        ・論点：【構造化データの活用状況】【AIが理解しやすいセマンティック構造】【ゼロクリック検索に対応する定義文の有無】

        ■5. 競合を圧倒する「新規コンテンツ案」10選
        ・（タイトル）（狙い）（盛り込むべき具体的キーワード）を10個。

        ■6. 戦略的キーワード・ポートフォリオ（10選）

        ■7. 最優先改善アクション（守りと攻め）
        【守りのアクション（即修正）】
        ・「どのページの、どの要素をどう直すか」をピンポイントで3つ。
        【攻めのアクション（新規/拡大）】
        ・「どのキーワードを狙い、どんな導線を作るか」を具体的に2つ。

        ■8. リライト推奨ページと改善の方向性
        ・対象ページ、現在の課題、リライト後の具体的構成（H2, H3の例）を提示。
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "あなたは技術、心理、戦略に精通したトップコンサルタントです。曖昧な表現を排し、事実に基づき冷徹に指摘してください。"},
                {"role": "user", "content": phase2_prompt}
            ],
            temperature=0.0
        )
        
        st.header("🛡️ プロフェッショナル実務診断レポート")
        st.markdown(response.choices[0].message.content)
