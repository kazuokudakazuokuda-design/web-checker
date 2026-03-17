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
    """サイトのビジネス構造を抽出"""
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
        return "\n".join(lines)[:7500] 
    except Exception as e:
        return f"取得失敗: {str(e)}"

# 状態管理（ステップ1が終わったかどうかを記憶）
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

# --- STEP 1: 戦略基準の定義 ---
if submit_btn and my_url and comp1_url:
    with st.spinner("サイト群から業界の勝ち筋を抽出中..."):
        st.session_state.my_data = get_site_content(my_url)
        st.session_state.c1_data = get_site_content(comp1_url)
        st.session_state.c2_data = get_site_content(comp2_url) if comp2_url else "データなし"

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
    
    # --- STEP 2: 詳細診断へのボタン ---
    if st.button("STEP 2: この基準で詳細診断を実行する"):
        with st.spinner("基準に基づき全サイトを精密診断中..."):
            diag_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "あなたは冷徹なストラテジストです。提示された5大戦略基準を『物差し』として、自社サイトを厳格に点数化し診断してください。"},
                    {"role": "user", "content": f"""
以下の基準に基づき、自社・競合の比較診断レポートを作成せよ。

【定義された5大戦略基準】:
{st.session_state.standards}

【解析対象データ】
自社: {st.session_state.my_data} / 競合A: {st.session_state.c1_data} / 競合B: {st.session_state.c2_data}

以下の構成で出力してください。

■0. ポジショニング分析
・（特徴）/（競合比較）/（総合評価）を上記基準に照らして記述。

■1. コンテンツの「実務解像度」の分析
・総合コメント：基準に照らした自社・競合の情報の質（一次情報の有無）の比較。
・論点評価（自社）：【実績の裏付け】〇点/40点、【提供価値の具体的証明】〇点/30点、【更新頻度と熱量】〇点/30点
・具体的指摘：基準を満たすために自社のどの記述が「抽象的」か特定。

■2. 成約導線と「顧客心理ハードル」の分析
・総合コメント：ユーザーを「今すぐ決断」させる力の格差。
・論点評価（自社）：【初見3秒での価値理解】〇点/40点、【プロセスの明快さ】〇点/30点、【非言語情報の質】〇点/30点
・具体的指摘：基準を満たす上で、現在のバナー、写真、コピーのどこが「離脱」を招いているか。

■3. EEAT（信頼性と専門的根拠）の診断
・総合コメント：権威性と信頼性の格差。
・論点評価（自社）：【発信主体の実績の厚み】〇点/40点、【外部による客観的評価】〇点/30点、【裏付けデータの提示】〇点/30点
・具体的指摘：基準を確信させるために、自社に不足している具体的要素。

■4. SEO / LLMO（AI検索）適応状況
・論点：【構造的回答】【セマンティック構造】【結論の提示速度】

■5. 新規コンテンツ案 10選（5大戦略基準を強化する内容）
■6. 戦略的キーワード・ポートフォリオ（10選）
■7. 最優先改善アクション（守りと攻め）
■8. リライト推奨ページと改善課題
"""}
                ],
                temperature=0.0
            )
            st.divider()
            st.header("🛡️ 戦略・実務詳細診断レポート")
            st.markdown(diag_response.choices[0].message.content)
