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
        # 会社名の取得試行
        og_site_name = soup.find("meta", property="og:site_name")
        site_title = og_site_name["content"] if og_site_name else soup.title.string if soup.title else url
        
        for s in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            s.decompose()
        lines = []
        for tag in soup.find_all(['title', 'h1', 'h2', 'h3', 'h4', 'p', 'li', 'dt', 'dd', 'table']):
            text = tag.get_text().strip()
            if len(text) > 2:
                lines.append(f"<{tag.name}>{text}")
        content = "\n".join(lines)[:8000]
        return {"name": site_title, "url": url, "content": content}
    except Exception as e:
        return {"name": url, "url": url, "content": "データ取得エラー"}

# コピー用JavaScript
def copy_to_clipboard_js(text):
    escaped_text = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    js_code = f"""
    <script>
    function copyText() {{
        const text = `{escaped_text}`;
        navigator.clipboard.writeText(text).then(() => {{
            alert("レポートをコピーしました！資料作成にご活用ください。");
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
    my_url_in = st.text_input("自社URL", placeholder="https://example.com")
    comp1_url_in = st.text_input("競合A", placeholder="https://competitor-a.com")
    comp2_url_in = st.text_input("競合B", placeholder="（任意）")
    if st.button("STEP 1: 業界を特定する"):
        if not my_url_in or not comp1_url_in:
            st.error("自社と競合AのURLは必須です。")
        else:
            with st.spinner("診断中"):
                st.session_state.my_res = get_site_content(my_url_in)
                st.session_state.c1_res = get_site_content(comp1_url_in)
                st.session_state.c2_res = get_site_content(comp2_url_in) if comp2_url_in else {"name": "なし", "url": "-", "content": "なし"}
                
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
                    {"role": "system", "content": "あなたは丁寧かつ論理的な超一流のWebストラテジストです。すべて『です・ます調』で、1項目400-600文字の濃厚な分析を行ってください。"},
                    {"role": "user", "content": f"""
【対象業界】: {st.session_state.industry}
【自社】: {st.session_state.my_res['name']} ({st.session_state.my_res['url']})
【競合A】: {st.session_state.c1_res['name']} ({st.session_state.c1_res['url']})
【競合B】: {st.session_state.c2_res['name']} ({st.session_state.c2_res['url']})

以下の構成で出力してください。

### ■ 診断対象
- **自社**: {st.session_state.my_res['name']} ({st.session_state.my_res['url']})
- **競合A**: {st.session_state.c1_res['name']} ({st.session_state.c1_res['url']})
- **競合B**: {st.session_state.c2_res['name']} ({st.session_state.c2_res['url']})

### ■ 業界Web戦略基準の定義
この業界で成約を勝ち取るために必須となる5大基準を、理由と評価ポイント（各3つ）を添えて詳細に出力してください。

### ■0. ポジショニング分析（Web表記ベース）
- 自社のポジション / 競合・業界との状況 / 自社の課題
- 各項目400文字以上の長文で記述。
### **全体評価：〇点**

### ■1. コンテンツの「実務解像度」の分析
### **〇点**
- **【実績の裏付け】** / **【提供価値の具体的証明】**
- 競合の数字や固有名詞と対比し、自社の表現がどのように信頼性に影響しているか分析してください。

### ■2. 成約導線と「顧客心理ハードル」の分析
### **〇点**
- **【初見3秒での価値理解】** / **【プロセスの明快さ】** / **【非言語情報の質】**
- 具体的な改善ポイントを提示してください。

### ■3. EEAT（信頼性と専門的根拠）の徹底診断
### **〇点**
- 信頼の証拠（実名レビュー、写真、資格、表彰）の有無について格差を追求してください。

### ■4. SEO / LLMO（AI検索）適応状況の徹底診断
- 不足している専門用語を10個以上列挙し、その必要性を解説してください。

### ■5. 競合を圧倒する「新規コンテンツ案」10選
各案200文字以上の狙いを添えてください。

### ■6. 最優先改善アクションプラン
🚨【最優先】、⚠️【優先】、💡【次の課題】を、です・ます調で具体的に記述してください。
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
