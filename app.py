import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# 1. 画面構成
st.set_page_config(page_title="🛡️ 実務戦略診断レポート", layout="wide")
st.title("🛡️ 実務特化型 Web戦略診断")

# Secretsから読み込み
try:
    api_key = st.secrets["OPENAI_API_KEY"].strip().strip('"')
    client = OpenAI(api_key=api_key)
except:
    st.error("APIキーの設定を確認してください。")
    st.stop()

def get_site_content(url):
    """サイトの構造、テキスト、主要な内部リンクを抽出"""
    try:
        url = url.strip()
        if not url.startswith("http"): url = "https://" + url
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, "html.parser")
        
        # 不要要素の排除
        for s in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            s.decompose()
            
        lines = []
        # URL特定のために、主要なリンクテキストとhrefも少し拾う
        for tag in soup.find_all(['title', 'h1', 'h2', 'h3', 'h4', 'p', 'li', 'dt', 'dd', 'table', 'a']):
            if tag.name == 'a' and tag.get('href'):
                href = tag.get('href')
                if href.startswith('/') or url in href:
                    lines.append(f"[Link: {tag.get_text().strip()} -> {href}]")
            else:
                text = tag.get_text().strip()
                if len(text) > 2:
                    lines.append(f"<{tag.name}>{text}")
        
        return "\n".join(lines)[:8000] 
    except Exception as e:
        return f"取得失敗: {str(e)}"

# 状態管理
if 'step2_ready' not in st.session_state:
    st.session_state.step2_ready = False
    st.session_state.standards = ""

# 2. 入力フォーム
with st.form("input_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        my_url = st.text_input("自社URL", placeholder="分析対象URL")
    with col2:
        comp1_url = st.text_input("競合A", placeholder="比較対象URL")
    with col3:
        comp2_url = st.text_input("競合B", placeholder="（任意）")
    submit_btn = st.form_submit_button("STEP 1: 業界戦略を解読する")

if submit_btn and my_url and comp1_url:
    with st.spinner("業界の勝ち筋を抽出中..."):
        st.session_state.my_data = get_site_content(my_url)
        st.session_state.c1_data = get_site_content(comp1_url)
        st.session_state.c2_data = get_site_content(comp2_url) if comp2_url else "データなし"
        st.session_state.my_url_orig = my_url

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": f"以下のサイト情報を解析し、この業界で勝つための『Web5大戦略基準』を定義せよ。1.[基準名]、理由、評価ポイント(3つ)の形式で。\n\n自社:{st.session_state.my_data}\n競合:{st.session_state.c1_data}"}],
            temperature=0.0
        )
        st.session_state.standards = response.choices[0].message.content
        st.session_state.step2_ready = True

if st.session_state.step2_ready:
    st.subheader("🛡️ この業界を勝ち抜くWeb5大戦略基準")
    st.markdown(st.session_state.standards)
    
    if st.button("STEP 2: この基準で最新SEO/AI検索を含む詳細診断を実行"):
        with st.spinner("最新の検索アルゴリズムに照らして精密診断中..."):
            diag_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "あなたはGoogle検索アルゴリズムとLLMO（AI回答最適化）に精通したシニアストラテジストです。最低点を10点とし、技術的・戦略的欠陥を冷徹に指摘してください。"},
                    {"role": "user", "content": f"""
以下の基準に基づき、詳細診断レポートを作成せよ。

【定義された5大戦略基準】: {st.session_state.standards}
【自社データ】: {st.session_state.my_data} (BaseURL: {st.session_state.my_url_orig})
【競合データ】: {st.session_state.c1_data} / {st.session_state.c2_data}

以下の構成で出力してください。

■0. ポジショニング分析
・全体評価: 市場における現在のWeb戦闘力の判定（最低10点）。

■1. コンテンツの「実務解像度」の分析
全体評価：〇点　コメント
【実績の裏付け】コメント（競合対比）
【提供価値の具体的証明】コメント（競合対比）
【更新頻度】コメント（競合対比）

■2. 成約導線と「顧客心理ハードル」の分析
全体評価：〇点　コメント
【初見3秒での価値理解】コメント（競合対比）
【プロセスの明快さ】コメント（競合対比）
【非言語情報の質】コメント（競合対比）

■3. EEAT（信頼性と専門的根拠）の診断
全体評価：〇点　コメント
【発信主体の実績の厚み】コメント（競合対比）
【外部による客観的評価】コメント（競合対比）
【裏付けデータの提示】コメント（競合対比）

■4. SEO / LLMO（AI検索）適応状況の徹底診断
この項目は専門的な観点から詳細に回答せよ。
・【インテント適合度】: ユーザーの検索意図に対し、競合と比べて「結論の提示」がどれだけ遅いか。
・【セマンティック・ギャップ】: AI（LLM）が文脈を理解する際に不足している専門用語や関連概念の欠落。
・【EEATシグナルの脆弱性】: 著者情報や監修、構造化データ（JSON-LD）が不足していることによる検索順位への悪影響。
・【LLMO（AI回答）適応度】: PerplexityやSearchGPTなどのAI検索エンジンが「このサイトを引用すべき」と判断する情報の整理状況。

■5. 競合を圧倒する「新規コンテンツ案」10選
自社データに存在せず、かつ5大戦略基準を強化し、検索需要（ロングテール）を総なめにする案。

■6. 戦略的キーワード・ポートフォリオ（10選）

■7. 最優先改善アクション（守りと攻め）
【守り（即修正）】3つ / 【攻め（拡大）】2つ

■8. リライト推奨ページと改善の方向性
自社サイト内から、修正すべきページを最大3つ特定せよ。
・対象ページ：[ページ名] (URL: 可能な限り正確なパスを記載)
・改善の方向性：[5大戦略基準に基づき、具体的にどう書き換えるか。特にタイトルタグや見出し、結論の配置について言及せよ]
"""}
                ],
                temperature=0.0
            )
            st.divider()
            st.header("🛡️ 戦略・実務詳細診断レポート")
            st.markdown(diag_response.choices[0].message.content)
