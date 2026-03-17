import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# 1. 画面構成
st.set_page_config(page_title="🛡️ 業界特化型 Web戦略診断", layout="wide")
st.title("🛡️ 業界特化型 Web戦略診断")

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

# 状態管理
if 'step' not in st.session_state:
    st.session_state.step = 1
    st.session_state.industry = ""

# サイドバー：URL入力
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
                st.session_state.my_url_orig = my_url
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": f"以下のサイト情報から、この3社が共通して属する『具体的業界名』のみを回答せよ。余計な枕詞は不要。\n\n自社:{st.session_state.my_data}\n競合:{st.session_state.c1_data}"}],
                    temperature=0.0
                )
                st.session_state.industry = response.choices[0].message.content.replace("業界", "")
                st.session_state.step = 2

# STEP 2 & 3: 業界確認から詳細診断まで一気に走らせる
if st.session_state.step >= 2:
    st.subheader("📌 業界確認と詳細診断の実行")
    industry_input = st.text_input("特定された業界（必要に応じて修正してください）", value=st.session_state.industry)
    
    if st.button("診断を開始する"):
        st.session_state.industry = industry_input
        with st.spinner("診断中"):
            # 業界基準の策定と詳細診断を1つのプロンプトで濃厚に実行
            diag_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "あなたはWebマーケティングとUI/UXの冷徹なシニアコンサルタントです。抽象的な議論を排し、Webサイト上の『具体的な記述・ボタン・導線・構造』の不備を指摘してください。褒め言葉は不要。一項目300文字以上の圧倒的情報量でえぐり出してください。最低点は10点。"},
                    {"role": "user", "content": f"""
【対象業界】: {st.session_state.industry}
【自社Webデータ】: {st.session_state.my_data}
【競合Webデータ】: {st.session_state.c1_data} / {st.session_state.c2_data}

まず冒頭に、この業界でWebサイトが問い合わせを獲得するために必須となる『Web5大戦略基準』を具体的・物理的な判断要素（例：解決事例の詳しさ、料金の細かさ等）で定義せよ。

その上で、以下の構成で超濃厚な比較診断レポートを作成せよ。各項目の点数は100点満点。

### ■0. ポジショニング分析（Web表記ベース）
- 自社のポジション / 競合・業界との状況 / 自社の課題
- **全体評価：〇点**

### ■1. コンテンツの「実務解像度」の分析
**〇点**
- **【実績の裏付け】**: 競合はどのページで、どんな数字やエピソードを出し、プロとしての説得力を構築しているか。対して、自社の「ただの紹介文」がなぜプロの仕事に見えないのか、具体的にどの記述が原因か。
- **【提供価値の具体的証明】**: ユーザーが「自分の悩みが解決する」と確信するまでの論理的ステップが、自社サイトのどの部分で断絶しているか。

### ■2. 成約導線と「顧客心理ハードル」の分析
**〇点**
- **【初見3秒での価値理解】**: スマホのファーストビューで「このサイトは自分に関係がある」と確信させる一言があるか。自社のバナーがいかにユーザーの悩みを無視しているか。
- **【プロセスの明快さ】**: 問い合わせボタンの配置、その後の予約フォームの項目数、完了までの心理的ストレスの有無。
- **【非言語情報の質】**: 写真素材の解像度や表情、図解の有無が、いかに「この会社は止まっている（古い）」という印象を植え付けているか。

### ■3. EEAT（信頼性と専門的根拠）の徹底診断
**〇点**
- **【発信主体の実績の厚み】**: 競合が「経験豊富」と書くために費やしている文字数や事例項目数に対し、自社がいかに「情報の出し惜しみ」をしているか。
- **【外部による客観的評価】**: 「お客様の声」に実名、写真、手書きの感想があるか。自社の「文字だけの感想」がなぜサクラに見えてしまうのか。

### ■4. SEO / LLMO（AI検索）適応状況の徹底診断
- **【インテント適合度】**: 検索ユーザーが「今すぐ知りたい結論（料金・場所・実績）」がどこに隠れているか。無駄なスクロールを強いる構成の欠陥。
- **【セマンティック・ギャップ】**: AIが専門家と認定するために不可欠なキーワードの欠落（具体的に列挙せよ）。

### ■5. 競合を圧倒する「新規コンテンツ案」10選
自社サイトに**現時点で絶対に載っていない**、競合の隙を突く具体案。各案100文字以上の狙いを添えて。

### ■6. ホームページ最優先改善アクション
- **🚨【最優先（緊急）】**: 信頼を棄損している要素（2点）。
- **⚠️【優先（重要）】**: 競合に負けているWeb表記（2点）。
- **💡【次の課題（拡張）】**: 追加すべきコンテンツ（2点）。
"""}
                ],
                temperature=0.0
            )
            st.divider()
            st.markdown(diag_response.choices[0].message.content)
