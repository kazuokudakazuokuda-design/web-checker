import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# 1. 画面構成
st.set_page_config(page_title="🛡️ 戦略・実務診断レポート", layout="wide")
st.title("🛡️ 実務特化型 Web戦略診断")

# Secretsから読み込み
try:
    api_key = st.secrets["OPENAI_API_KEY"].strip().strip('"')
    client = OpenAI(api_key=api_key)
except:
    st.error("APIキーの設定を確認してください。")
    st.stop()

def get_site_content(url):
    """サイトのビジネス構造、テキスト、リンク、階層を抽出"""
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
        for tag in soup.find_all(['title', 'h1', 'h2', 'h3', 'h4', 'p', 'li', 'dt', 'dd', 'table', 'a']):
            if tag.name == 'a' and tag.get('href'):
                href = tag.get('href')
                if href.startswith('/') or url in href:
                    lines.append(f"[URL_Reference: {tag.get_text().strip()} -> {href}]")
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
            messages=[{"role": "user", "content": f"以下のサイト情報を解析し、この業界で勝つための『Web5大戦略基準』を定義せよ。特定業界の偏りを排し、ビジネスの本質から定義すること。1.[基準名]、理由、評価ポイント(3つ)の形式で。\n\n自社:{st.session_state.my_data}\n競合:{st.session_state.c1_data}"}],
            temperature=0.0
        )
        st.session_state.standards = response.choices[0].message.content
        st.session_state.step2_ready = True

if st.session_state.step2_ready:
    st.subheader("🛡️ この業界を勝ち抜くWeb5大戦略基準")
    st.markdown(st.session_state.standards)
    
    if st.button("STEP 2: この基準で詳細診断を実行"):
        with st.spinner("実務とWebの両面から徹底診断中..."):
            diag_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "あなたは、業界の道理とWeb戦略の両方に精通し、忖度なしに事実をえぐり出すストラテジストです。最低点を10点とし、言い逃れできない証拠に基づき診断してください。"},
                    {"role": "user", "content": f"""
以下の定義とデータに基づき、詳細診断レポートを作成せよ。

【定義された5大戦略基準】: {st.session_state.standards}
【自社データ】: {st.session_state.my_data} (Base: {st.session_state.my_url_orig})
【競合データ】: {st.session_state.c1_data} / {st.session_state.c2_data}

以下の構成で出力すること：

■0. ポジショニング分析
・（自社のポジション）: サイトに実在するページや記載内容から見える、現在の立ち位置（事実のみ）。
・（競合・業界との状況）: 競合が保有するコンテンツや業界標準との比較。
・（自社の課題）: 上記2つの「事実の差」から導き出される、埋めるべき決定的なギャップ。
・全体評価: 市場における現在のWeb戦闘力の判定（最低10点）。

■1. コンテンツの「実務解像度」の分析
全体評価：〇点　コメント
【実績の裏付け】競合はこうだが自社はこうなっている、という具体的対比（情報の鮮度・運用実態を含む）。
【提供価値の具体的証明】数字やプロセス、生々しい証拠の有無についての具体的対比。
【更新頻度】最終更新や情報の熱量が顧客心理に与える影響。
※具体的指摘：基準を満たすために不足している、または専門用語の使い方がズレている要素。

■2. 成約導線と「顧客心理ハードル」の分析
全体評価：〇点　コメント
【初見3秒での価値理解】キャッチコピーとビジュアルが検索意図に即応しているか。
【プロセスの明快さ】取引開始までの心理的・物理的ハードルの有無。
【非言語情報の質】写真や素材が「信頼」を醸成しているか、それとも「不信」を招いているか。
※具体的指摘：スマホ環境も含め、ユーザーがどこで「不安・面倒」を感じ離脱しているか。

■3. EEAT（信頼性と専門的根拠）の診断
全体評価：〇点　コメント
【発信主体の実績の厚み】実務家としての厚みが伝わるか（単なる紹介に留まっていないか）。
【外部による客観的評価】第三者の証明があるか。
【裏付けデータの提示】AIやユーザーを納得させる論理的根拠。

■4. SEO / LLMO（AI検索）適応状況の徹底診断
・【インテント適合度】: ユーザーの検索意図に対し「結論」を出す速さ。
・【セマンティック・ギャップ】: 業界の文脈を理解させるための語彙や関連概念の欠落。
・【EEATシグナルの脆弱性】: 構造化データや専門性の証明不足が招く機会損失。
・【LLMO適応度】: AI検索（Perplexity等）がサイトを信頼できるソースとして引用しやすい構造か。

■5. 競合を圧倒する「新規コンテンツ案」10選
自社データに存在せず、5大戦略基準を強化し、ユーザーの負の感情を解消する案。

■6. 戦略的キーワード・ポートフォリオ（10選）

■7. 優先順位別・改善アクション
【最優先（緊急）】: 安全性や信頼性を激しく棄損している不備、業界で必須なのに欠落している要素（2つ）。
【優先（重要）】: 安全性や信頼性に懸念がある、または競合に著しく劣る要素（2つ）。
【次の課題（拡張）】: 信頼性は保てているが、さらに差別化するための要素（2つ）。

■8. リライト推奨ページと改善の方向性
自社サイトから3ページ選定。
・対象ページ：[ページ名] (URL)
・改善の方向性：[5大戦略基準に基づき、具体的にどう書き換えるか。タイトル・見出し・結論配置に触れること]
"""}
                ],
                temperature=0.0
            )
            st.divider()
            st.header("🛡️ 戦略・実務詳細診断レポート")
            st.markdown(diag_response.choices[0].message.content)
