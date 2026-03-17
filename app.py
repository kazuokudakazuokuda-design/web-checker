import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# 1. 画面構成
st.set_page_config(page_title="🛡️ 実務Web戦略診断", layout="wide")
st.title("🛡️ 実務特化型 Web戦略診断")

# Secrets
try:
    api_key = st.secrets["OPENAI_API_KEY"].strip().strip('"')
    client = OpenAI(api_key=api_key)
except:
    st.error("APIキーの設定を確認してください。")
    st.stop()

def get_site_content(url):
    try:
        url = url.strip()
        if not url.startswith("http"): url = "https://" + url
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, "html.parser")
        for s in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            s.decompose()
        lines = []
        for tag in soup.find_all(['title', 'h1', 'h2', 'h3', 'h4', 'p', 'li', 'dt', 'dd', 'table']):
            text = tag.get_text().strip()
            if len(text) > 2:
                lines.append(f"<{tag.name}>{text}")
        return "\n".join(lines)[:8000] 
    except Exception as e:
        return f"取得失敗: {str(e)}"

if 'step2_ready' not in st.session_state:
    st.session_state.step2_ready = False
    st.session_state.standards = ""

with st.form("input_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        my_url = st.text_input("自社URL")
    with col2:
        comp1_url = st.text_input("競合A")
    with col3:
        comp2_url = st.text_input("競合B")
    submit_btn = st.form_submit_button("STEP 1: 業界要件を特定する")

if submit_btn and my_url and comp1_url:
    with st.spinner("業界のWeb勝ち筋を抽出中..."):
        st.session_state.my_data = get_site_content(my_url)
        st.session_state.c1_data = get_site_content(comp1_url)
        st.session_state.c2_data = get_site_content(comp2_url) if comp2_url else "データなし"
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": f"以下のサイト情報を解析し、この業界（具体的に何業界か明示せよ）でWebサイトが勝つための『5大戦略基準』を定義せよ。一般論は禁止。ユーザーが『このサイトで問い合わせるか』を決める具体的・物理的な判断基準を5つ出せ。1.[基準名]、理由、評価ポイント(3つ)の形式で。\n\n自社:{st.session_state.my_data}\n競合:{st.session_state.c1_data}"}],
            temperature=0.0
        )
        st.session_state.standards = response.choices[0].message.content
        st.session_state.step2_ready = True

if st.session_state.step2_ready:
    st.subheader("🛡️ 特定された業界Web戦略基準")
    st.markdown(st.session_state.standards)
    
    if st.button("STEP 2: 詳細診断（EEAT/SEO徹底解析）を実行"):
        with st.spinner("最新アルゴリズムに基づき精密診断中..."):
            diag_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "あなたはGoogle検索品質評価ガイドラインおよびLLMO（AI回答最適化）に精通したシニアWebストラテジストです。最低点を10点とし、競合との『情報格差』を徹底的に暴いてください。"},
                    {"role": "user", "content": f"""
以下の定義とWebデータに基づき、比較診断レポートを作成せよ。

【定義された戦略基準】: {st.session_state.standards}
【自社Webデータ】: {st.session_state.my_data}
【競合Webデータ】: {st.session_state.c1_data} / {st.session_state.c2_data}

以下の構成で出力すること。

■0. ポジショニング分析（Web表記ベース）
・（自社のポジション）/（競合・業界との状況）/（自社の課題）/ 全体評価（最低10点）。

■1. コンテンツの「実務解像度」の分析
全体評価：〇点　/ 【実績の裏付け】【提供価値の具体的証明】【更新頻度】（競合対比コメント）

■2. 成約導線と「顧客心理ハードル」の分析
全体評価：〇点　/ 【初見3秒での価値理解】【プロセスの明快さ】【非言語情報の質】（スマホ環境含む）

■3. EEAT（信頼性と専門的根拠）の徹底診断
全体評価：〇点　コメント
この項目は、サイト全体の信頼性を担保する『証拠』の有無を診断せよ。
・【発信主体の実績の厚み】: 「紹介」ではなく、過去の具体的な数字、期間、プロジェクト規模など、実力の証明となる記述が競合と比べて何文字・何項目不足しているか。
・【外部による客観的評価】: お客様の声（実名・写真の有無）、メディア掲載実績、公的資格、団体所属、表彰などの掲載状況。競合が載せているのに自社が載せていない要素を特定せよ。
・【裏付けデータの提示】: 主張の根拠となる統計データ、公的機関へのリンク、自社調査結果など、論理的根拠の有無。

■4. SEO / LLMO（AI検索）適応状況の徹底診断
最新の検索アルゴリズムと、AI検索エンジンに対する適応状況を詳細に回答せよ。
・【インテント適合度】: ユーザーの検索意図（悩み）に対し、ページを開いてから「答え」に辿り着くまでのスクロール量や構成の悪さを指摘せよ。
・【セマンティック・ギャップ】: AIがこのサイトを専門家と見なすために必要な「共起語」や「関連トピック」の欠落。具体的に、競合が多用しているが自社サイトに不足している専門用語を列挙せよ。
・【LLMO適応度】: PerplexityやSearchGPTが情報を抽出しやすいリスト構造、Q&A形式、構造化データ（JSON-LD）の活用状況を診断せよ。

■5. 競合を圧倒する「新規コンテンツ案」10選
自社サイトに未掲載で、検索意図を網羅し、競合の隙を突くコンテンツ案（タイトル、狙い、主要キーワードを各300文字程度の熱量で想定せよ）。

■6. 戦略的キーワード・ポートフォリオ（10選）

■7. ホームページ最優先改善アクション
【最優先（緊急）】: 信頼性を棄損している不備（2つ）。
【優先（重要）】: 競合に著しく劣るWeb上の表記（2つ）。
【次の課題（拡張）】: 差別化のための追加コンテンツ案（2つ）。
"""}
                ],
                temperature=0.0
            )
            st.divider()
            st.header("🛡️ 戦略・実務詳細診断レポート")
            st.markdown(diag_response.choices[0].message.content)
