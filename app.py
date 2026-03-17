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

# 状態管理
if 'step' not in st.session_state:
    st.session_state.step = 1
    st.session_state.industry = ""
    st.session_state.standards = ""

# 入力フォーム（STEP 1）
with st.sidebar:
    st.header("🔍 解析対象設定")
    my_url = st.text_input("自社URL", value="https://namihaya.biz/")
    comp1_url = st.text_input("競合A", value="https://uehonmachi-law.com/")
    comp2_url = st.text_input("競合B")
    if st.button("STEP 1: サイト解析開始"):
        with st.spinner("サイトデータを抽出中..."):
            st.session_state.my_data = get_site_content(my_url)
            st.session_state.c1_data = get_site_content(comp1_url)
            st.session_state.c2_data = get_site_content(comp2_url) if comp2_url else "データなし"
            st.session_state.my_url_orig = my_url
            
            # 業界の特定
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": f"以下のサイト情報から、この3社が属する『業界名』のみを回答せよ。余計な説明は不要。\n\n自社:{st.session_state.my_data}\n競合:{st.session_state.c1_data}"}],
                temperature=0.0
            )
            st.session_state.industry = response.choices[0].message.content.replace("業界", "")
            st.session_state.step = 2

# --- STEP 2: 業界確認と基準定義 ---
if st.session_state.step >= 2:
    st.subheader("📌 STEP 2: 業界の確認と戦略基準の定義")
    industry_input = st.text_input("特定された業界（修正が必要な場合は書き換えてください）", value=st.session_state.industry)
    
    if st.button("この業界で戦略基準を定義する"):
        st.session_state.industry = industry_input
        with st.spinner(f"{st.session_state.industry}業界のWeb勝ち筋を抽出中..."):
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": f"{st.session_state.industry}業界において、ユーザーがWebサイトで『ここに問い合わせるか』を決める具体的・物理的な判断基準（判断の物差し）を5つ定義せよ。一般論は禁止。\n1.[基準名]\n-（理由）: 重要性\n-（評価ポイント）: 具体的なチェック要素3つ\nの形式で。"}],
                temperature=0.0
            )
            st.session_state.standards = response.choices[0].message.content
            st.session_state.step = 3

# --- STEP 3: 詳細診断の実行 ---
if st.session_state.step >= 3:
    st.divider()
    st.markdown(f"### 🛡️ {st.session_state.industry}業界 Web戦略基準")
    st.info(st.session_state.standards)
    
    if st.button("STEP 3: 最終詳細診断を実行"):
        with st.spinner("Web上の事実格差をえぐり出し中..."):
            diag_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "あなたは冷徹なWebストラテジストです。見出し、改行、太字を多用し、視覚的に分かりやすく、かつ事実に基づき厳格に診断してください。最低点は10点とします。"},
                    {"role": "user", "content": f"""
以下の基準に基づき、Webサイトに限定した比較診断レポートを作成せよ。

【定義された戦略基準】: {st.session_state.standards}
【自社Webデータ】: {st.session_state.my_data}
【競合Webデータ】: {st.session_state.c1_data} / {st.session_state.c2_data}

以下の構成で出力すること。

### ■0. ポジショニング分析（Web表記ベース）
- **自社のポジション**: 現在のサイトの強み、ページ構成（事実のみ）。
- **競合・業界との状況**: 競合がWeb上で展開しているコンテンツとの比較。
- **自社の課題**: サイト上の情報量の差が生んでいる決定的ギャップ。
- **全体評価**: **{st.session_state.industry}業界におけるWeb戦闘力：〇点** / 100点

### ■1. コンテンツの「実務解像度」の分析
**全体評価：〇点**
- **【実績の裏付け】**: 競合対比コメント。
- **【提供価値の具体的証明】**: 数字、図解、プロセスの掲載状況。
- **【更新頻度】**: 情報の鮮度が信頼に与えるダメージ。
> **具体的指摘**: どのページに何の情報を追加すべきか。

### ■2. 成約導線と「顧客心理ハードル」の分析
**全体評価：〇点**
- **【初見3秒での価値理解】**: ファーストビューのコピーの即応性。
- **【プロセスの明快さ】**: 申し込みまでのステップ表示。
- **【非言語情報の質】**: 写真・素材の質と信頼感。
> **具体的指摘**: スマホ環境での離脱ポイントを特定。

### ■3. EEAT（信頼性と専門的根拠）の徹底診断
**全体評価：〇点**
- **【発信主体の実績の厚み】**: 実力の証明となる記述量（文字数・項目数）の格差。
- **【外部による客観的評価】**: お客様の声（実名・写真）、メディア実績等の掲載状況。
- **【裏付けデータの提示】**: 論理的根拠となるデータの有無。

### ■4. SEO / LLMO（AI検索）適応状況の徹底診断
- **【インテント適合度】**: ユーザーの「答え」に辿り着くまでのスクロール量や構成の悪さ。
- **【セマンティック・ギャップ】**: AIに専門家と認めさせるために不足している専門用語を列挙。
- **【LLMO適応度】**: AI検索（Perplexity等）が引用しやすいリスト構造、Q&A形式の活用状況。

### ■5. 競合を圧倒する「新規コンテンツ案」10選
自社サイトに**現時点で絶対に載っていない**案を、タイトル・狙い・主要キーワード含め具体的に。

### ■6. 戦略的キーワード・ポートフォリオ（10選）

### ■7. 優先順位別・ホームページ改善アクション
- **🚨【最優先（緊急）】**: 安全性・信頼性を**激しく棄損**している、または業界で必須なのにサイトにない要素（2点）。
- **⚠️【優先（重要）】**: 安全性・信頼性に**懸念**がある、または競合に著しく劣る要素（2点）。
- **💡【次の課題（拡張）】**: さらに差別化するための追加コンテンツ（2つ）。
"""}
                ],
                temperature=0.0
            )
            st.divider()
            st.markdown("## 🛡️ 戦略・実務詳細診断レポート")
            st.markdown(diag_response.choices[0].message.content)
