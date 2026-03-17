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
        for s in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            s.decompose()
        lines = []
        for tag in soup.find_all(['title', 'h1', 'h2', 'h3', 'h4', 'p', 'li', 'dt', 'dd', 'table']):
            text = tag.get_text().strip()
            if len(text) > 2:
                lines.append(f"<{tag.name}>{text}")
        content = "\n".join(lines)[:8000]
        return content if len(content) > 100 else "データ取得制限あり"
    except Exception as e:
        return "データ取得エラー"

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
                st.session_state.my_data = get_site_content(my_url)
                st.session_state.c1_data = get_site_content(comp1_url)
                st.session_state.c2_data = get_site_content(comp2_url) if comp2_url else "なし"
                st.session_state.urls = {"my": my_url, "c1": comp1_url, "c2": comp2_url if comp2_url else "-"}
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": f"業界名を回答せよ。余計な言葉は不要。\n\n自社:{st.session_state.my_data}\n競合:{st.session_state.c1_data}"}],
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
3. 各項目500文字以上の圧倒的な文章量で、具体的記述や構造の欠陥を指摘してください。
4. 点数は見出しの直後に配置し、必ず ### **〇〇点** という形式で記述してください。"""},
                    {"role": "user", "content": f"""
【対象業界】: {st.session_state.industry}
【自社URL】: {st.session_state.urls['my']}
【競合A URL】: {st.session_state.urls['c1']}
【競合B URL】: {st.session_state.urls['c2']}

以下の構成で、ユーザーの心理変化と技術的構造を深く診断するレポートを作成してください。

### ■ 診断対象
- **自社**: {st.session_state.urls['my']}
- **競合A**: {st.session_state.urls['c1']}
- **競合B**: {st.session_state.urls['c2']}

### ■ 業界Web戦略基準の定義
この業界で成約を勝ち取るために必須となる5大基準を、理由と評価ポイント（各3つ）を添えて出力してください。

### ■0. ポジショニング分析（Web表記ベース）
### **〇点**
- 自社のポジション / 競合・業界との状況 / 自社の課題を、各500文字以上の長文で客観的に説明してください。

### ■1. コンテンツの「実務解像度」の分析
### **〇点**
- **【実績の裏付け】**: 競合が提示している具体的数字やプロジェクト例と対比し、自社の表現がどのように信頼性に影響しているか分析してください。
- **【提供価値の具体的証明】**: ユーザーが解決を確信するまでの論理的ステップが、サイトのどの記述で欠落しているかを指摘してください。

### ■2. 成約導線と「顧客心理ハードル」の分析
### **〇点**
- **【初見3秒での価値理解】**: スマホのファーストビューでの情報提示の適否。自社の意図が正しく伝わっているかを分析してください。
- **【プロセスの明快さ】**: 相談から完了までのステップが視覚化されているか、心理的負荷を分析してください。
- **【非言語情報の質】**: 画像素材、配色、レイアウトがブランドの信頼性に与える影響を詳述してください。

### ■3. EEAT 診断
※Webサイトの品質評価で重要視する「経験・専門性・権威性・信頼性」の4要素
### **〇点**
- **【経験（Experience）】**: 実体験に基づく一次情報の有無。具体的な工程や独自の工夫が記述されているかを診断してください。
- **【専門性（Expertise）】**: 業界知識の網羅性、技術解説の解像度、実務レベルの情報の深さを分析してください。
- **【権威性（Authoritativeness）】**: 業界団体への所属、保有資格、受賞歴、メディア掲載等の客観的な格付けの視覚化状況を判定してください。
- **【信頼性（Trustworthiness）】**: 実名・写真付き実績、最新の更新状況、運営者情報の詳細度など、情報の透明性を客観的に分析してください。

### ■4. SEO / LLMO 診断
### **〇点**
- **【インテント適合度と結論到達スピード】**: 検索意図に対し、数スクロール以内に回答（価格・納期・実績等）が配置されているかを診断してください。
- **【サイテーション（外部言及）の状況】**: 引用価値のある独自データや独自図解の有無。AIが「回答の引用元」として選定するための要素を分析してください。
- **【情報の鮮度（Freshness）】**: 最終更新日、法改正や業界トレンドの反映状況を確認し、情報の古さが検索評価に与える影響を指摘してください。
- **【セマンティック・ギャップ（専門用語5個）】**: AI検索が専門性を認識するために不可欠な業界用語を「厳選して5個」列挙し、その欠落による評価損失を解説してください。

### ■5. 診断に基づく新規コンテンツ案 5案
自社サイトに未掲載で、競合の隙を突く具体案。各案ごとに200文字以上の狙いを記述してください。

### ■6. 最優先改善アクションプラン
- 【最優先】
  1. （具体的な要素と変更内容）
  2. （具体的な要素と変更内容）
- 【優先】
  1. （具体的な要素と変更内容）
  2. （具体的な要素と変更内容）
- 【次の課題】
  1. （具体的な要素と変更内容）
  2. （具体的な要素と変更内容）
※「どのページの、どの要素を、どのように書き換えるか」を、です・ます調で具体的に記述してください。
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
