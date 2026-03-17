import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import streamlit.components.v1 as components

# 1. 画面構成
st.set_page_config(page_title="🛡️ 業界特化型 Web戦略診断", layout="wide")
st.title("🛡️ 業界特化型 Web戦略診断")
st.caption("※あくまで生成AIによる一次診断としてご利用ください。情報が不確かな場合があります。")

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
        
        # Meta Descriptionの取得
        meta_desc = soup.find("meta", attrs={"name": "description"})
        description = meta_desc["content"].strip() if meta_desc else "設定なし"
        
        # 本文テキストの抽出
        for s in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            s.decompose()
        lines = []
        for tag in soup.find_all(['title', 'h1', 'h2', 'h3', 'h4', 'p', 'li', 'dt', 'dd', 'table']):
            text = tag.get_text().strip()
            if len(text) > 2:
                lines.append(f"<{tag.name}>{text}")
        content = "\n".join(lines)[:8000]
        
        return {"description": description, "content": content}
    except Exception as e:
        return {"description": "取得エラー", "content": "データ取得エラー"}

# レポート一括コピー用JavaScript
def copy_to_clipboard_js(text):
    escaped_text = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    js_code = f"""
    <script>
    function copyText() {{
        const text = `{escaped_text}`;
        navigator.clipboard.writeText(text).then(() => {{
            alert("レポートをコピーしました！");
        }});
    }}
    </script>
    <button onclick="copyText()" style="
        background-color: #ff4b4b; color: white; border: none; padding: 10px 20px;
        border-radius: 5px; cursor: pointer; font-weight: bold; width: 100%; margin-bottom: 20px;
    ">📋 レポートをコピーする（Markdown形式）</button>
    """
    return components.html(js_code, height=70)

if 'step' not in st.session_state:
    st.session_state.step = 1
    st.session_state.industry = ""
    st.session_state.full_report = ""

with st.sidebar:
    st.header("🔍 解析対象設定")
    my_url = st.text_input("自社URL", placeholder="https://example.com")
    comp1_url = st.text_input("競合A", placeholder="https://competitor-a.com")
    comp2_url = st.text_input("競合B", placeholder="（任意）")
    if st.button("STEP 1: 業界を特定する"):
        if not my_url or not comp1_url:
            st.error("自社と競合AのURLは必須です。")
        else:
            with st.spinner("診断中"):
                st.session_state.my_res = get_site_content(my_url)
                st.session_state.c1_res = get_site_content(comp1_url)
                st.session_state.c2_res = get_site_content(comp2_url) if comp2_url else {"description": "なし", "content": "なし"}
                st.session_state.urls = {"my": my_url, "c1": comp1_url, "c2": comp2_url if comp2_url else "-"}
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": f"業界名を回答せよ。余計な言葉は不要。\n\n自社:{st.session_state.my_res['content']}\n競合:{st.session_state.c1_res['content']}"}],
                    temperature=0.0
                )
                st.session_state.industry = response.choices[0].message.content.replace("業界", "")
                st.session_state.step = 2

if st.session_state.step >= 2:
    st.subheader("📌 業界確認と詳細診断の実行")
    industry_input = st.text_input("特定された業界", value=st.session_state.industry)
    
    if st.button("診断を開始する"):
        st.session_state.industry = industry_input
        with st.spinner("診断中"):
            diag_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": """あなたは丁寧かつ論理的、客観的な視点を持つ超一流のWebストラテジストです。
1. 文体はすべて「です・ます調」で統一してください。
2. 抽象的・詩的な表現を避け、具体的かつ客観的な事実に基づいた分析を行ってください。
3. 【最重要】AIの視覚的な推測（見た目、配色、バナー内の文字など）によるハルシネーションを厳禁します。テキストデータから読み取れる情報の「有無」と「構造」のみで語ってください。
4. 各診断項目は500文字以上の圧倒的な文章量で記述してください。
5. 点数（〇〇点）の算出は一切行わないでください。文章による論理的な分析に集中してください。
6. 冒頭の「診断対象」以外には、本文中にURLを一切記述しないでください。Markdownリンクも厳禁です。"""},
                    {"role": "user", "content": f"""
【対象業界】: {st.session_state.industry}
【自社URL】: {st.session_state.urls['my']}
【競合A URL】: {st.session_state.urls['c1']}
【競合B URL】: {st.session_state.urls['c2']}
【自社 Meta Description】: {st.session_state.my_res['description']}
【競合A Meta Description】: {st.session_state.c1_res['description']}
【競合B Meta Description】: {st.session_state.c2_res['description']}

以下の構成でレポートを作成してください。

### ■ 診断対象
- 自社: {st.session_state.urls['my']}
- 競合A: {st.session_state.urls['c1']}
- 競合B: {st.session_state.urls['c2']}

### ■ 各サイトのメタ・ディスクリプション（検索結果の説明文）
（自社と競合の設定内容をここに事実として列挙してください）

### ■ 業界Web戦略基準の定義
この業界で成約を勝ち取るために必須となる5大基準を、理由と評価ポイント（各3つ）を添えて詳細に出力してください。

### ■0. 自社、競合のホームページの現状
（※ビジネスモデルの分析ではなく、Webサイト上の表現・構造・コンテンツに限定して記述してください。評価・コメントは一切含めず、客観的事実の整理に徹すること。冒頭以外はURLを一切含めないこと。この指示文自体は出力しないこと）

* 自社の現状
* 競合の現状

### ■1. コンテンツの「実務解像度」の分析
- 【実績の裏付け】: 競合が提示している具体的数字やプロジェクト例と対比し、自社の表現がどのように信頼性に影響しているか分析してください。
- 【提供価値の具体的証明】: ユーザーが解決を確信するまでの論理的ステップが、サイト内の「テキスト記述」として成立しているか指摘してください。

### ■2. 成約導線と「顧客心理ハードル」の分析
- 【情報の優先順位】: ユーザーが求める結論（価格、事例等）が、テキスト構造上の上位に配置されているか診断してください。
- 【プロセスの明快さ】: 相談から完了までのステップが、テキストとして具体的に説明されているか、心理的負荷を分析してください。

### ■3. EEAT 診断
※Webサイトの品質評価で重要視する「経験・専門性・権威性・信頼性」の4要素
- 【経験（Experience）】: 実体験に基づく一次情報の具体的記述があるかを判定してください。
- 【専門性（Expertise）】: 技術解説の解像度、情報の深さをテキストから分析してください。
- 【権威性（Authoritativeness）】: 資格、所属団体、受賞歴等の記述の有無を判定してください。
- 【信頼性（Trustworthiness）】: 実名実績の有無、更新頻度、情報の透明性を客観的に分析してください。

### ■4. SEO / LLMO 診断
- 【インテント適合度と結論到達スピード】: メタ・ディスクリプションの内容と実際のコンテンツの整合性を含めて分析してください。
- 【サイテーション（外部言及）の状況】: 引用されるべき独自データや独自ノウハウの記述の有無を分析してください。
- 【情報の鮮度（Freshness）】: 最終更新日、トレンドの反映状況を指摘してください。
- 【セマンティック・ギャップ（専門用語5個）】: AI検索が専門性を認識するために不可欠な業界用語を「厳選して5個」列挙し、その欠落による評価損失を解説してください。

### ■5. 診断に基づく新規コンテンツ案 5案
各案ごとに200文字以上の狙いを記述してください。

### ■6. 最優先改善アクションプラン
- 【最優先】（具体的指示を2案）
- 【優先】（具体的指示を2案）
- 【次の課題】（具体的指示を2案）
※「どのページの、どの要素を、どのように書き換えるか」を、です・ます調で記述してください。
"""}
                ],
                temperature=0.0
            )
            st.session_state.full_report = diag_response.choices[0].message.content
            st.session_state.step = 3

if st.session_state.step >= 3:
    st.divider()
    st.markdown("## 🛡️ 戦略・実務詳細診断レポート")
    st.markdown(st.session_state.full_report)
    st.caption("※あくまで生成AIによる一次診断としてご利用ください。情報が不確かな場合があります。")
    st.divider()
    st.subheader("📋 レポートをコピーする")
    copy_to_clipboard_js(st.session_state.full_report)
