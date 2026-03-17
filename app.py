import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

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
        return content if len(content) > 100 else "データ取得制限あり（構造から推測）"
    except Exception as e:
        return "データ取得エラー（構造から推測）"

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
                st.session_state.c2_data = get_site_content(comp2_url) if comp2_url else "データなし"
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": f"以下のサイト情報から業界名を回答せよ。余計な言葉は不要。\n\n自社:{st.session_state.my_data}\n競合:{st.session_state.c1_data}"}],
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
                    {"role": "system", "content": """あなたは丁寧かつ論理的な超一流のWebストラテジストです。
1. 診断の文章はすべて「です・ます調」で統一し、敬意を払いつつも、専門家として厳しい指摘を丁寧に行ってください。
2. 命令形（～せよ、～しろ）は一切禁止です。「～を推奨いたします」「～への変更が必要です」といった表現を用いてください。
3. 各項目のコメントは最低400文字以上の圧倒的な文章量で、具体的な不備を指摘してください。
4. 点数は ### **〇〇点** という形式（見出しレベル3）で記述してください。"""},
                    {"role": "user", "content": f"""
【対象業界】: {st.session_state.industry}
【自社データ】: {st.session_state.my_data}
【競合データ】: {st.session_state.c1_data} / {st.session_state.c2_data}

以下の構成で、丁寧かつ濃厚なレポートを出力してください。

### ■ 業界Web戦略基準の定義
この業界で成約を勝ち取るために必須となる5大基準を、理由と評価ポイント（各3つ）を添えて出力してください。

### ■0. ポジショニング分析（Web表記ベース）
- 自社のポジション / 競合・業界との状況 / 自社の課題
- 各項目400文字以上の長文で、現在の格差を丁寧に説明してください。
### **全体評価：〇点**

### ■1. コンテンツの「実務解像度」の分析
### **〇点**
- **【実績の裏付け】** / **【提供価値の具体的証明】**
- 競合の数字や固有名詞と対比し、自社の表現がどのように信頼性に影響しているか分析してください。

### ■2. 成約導線と「顧客心理ハードル」の分析
### **〇点**
- **【初見3秒での価値理解】** / **【プロセスの明快さ】** / **【非言語情報の質】**
- ユーザーの心理的な動きを想像し、具体的な改善ポイントを提示してください。

### ■3. EEAT（信頼性と専門的根拠）の徹底診断
### **〇点**
- **【発信主体の実績の厚み】** / **【外部による客観的評価】**
- 公的なプロであることを示す証拠の有無について、競合との格差を追求してください。

### ■4. SEO / LLMO（AI検索）適応状況の徹底診断
- **【インテント適合度】** / **【セマンティック・ギャップ】**
- 不足している専門用語を10個以上列挙し、その必要性を丁寧に解説してください。

### ■5. 競合を圧倒する「新規コンテンツ案」10選
自社サイトに未掲載で、競合の隙を突く具体案を提案してください。各案200文字以上の狙いを添えてください。

### ■6. 最優先改善アクションプラン
- 🚨【最優先（緊急・信頼棄損修正）】
- ⚠️【優先（重要・競合対抗）】
- 💡【次の課題（拡張・差別化）】
※「どのページの、どの要素を、どのように変更・追加すべきか」を、です・ます調で具体的に記述してください。
"""}
                ],
                temperature=0.0
            )
            st.session_state.full_report = diag_response.choices[0].message.content
            st.session_state.step = 3

if st.session_state.step >= 3:
    st.divider()
    st.markdown("## 🛡️ 戦略・実務詳細診断レポート")
    
    # レポート表示
    st.markdown(st.session_state.full_report)
    
    st.caption("※あくまで生成AIによる一次診断としてご利用ください。情報が不確かな場合があります。")
    
    st.divider()
    
    # コピー用エリア
    st.subheader("📋 レポートをコピーする")
    with st.expander("Markdown形式でコピーする（クリックで展開）"):
        st.code(st.session_state.full_report, language="")
        st.caption("右上のアイコンをクリックしてコピーが可能です。")
