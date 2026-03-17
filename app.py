import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# 1. 画面構成
st.set_page_config(page_title="🛡️ 戦略・実務診断レポート", layout="wide")
st.title("🛡️ 実務特化型 Web戦略診断")

# Secretsから読み込み
try:
    api_key = st.secrets["OPENAI_API_KEY"].strip().strip('"').replace(' ', '')
    client = OpenAI(api_key=api_key)
except:
    st.error("APIキーの設定を確認してください。")
    st.stop()

def get_site_content(url):
    """サイトの文字情報を拾ってくる関数"""
    try:
        url = url.strip()
        if not url.startswith("http"): url = "https://" + url
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, "html.parser")
        for s in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            s.decompose()
        # 取得範囲を絞り込み、純粋なコンテンツだけを抽出
        elements = soup.find_all(["title", "h1", "h2", "h3", "p", "li"])
        content = "\n".join([e.get_text().strip() for e in elements if len(e.get_text().strip()) > 5])
        return content[:4000] # 文字数を絞って精度を上げる
    except Exception as e:
        return f"取得失敗: {str(e)}"

# 2. 入力フォーム
with st.form("input_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        my_url = st.text_input("自社URL", placeholder="https://namihaya.biz/")
    with col2:
        comp1_url = st.text_input("競合A", placeholder="https://uehonmachi-law.com/")
    with col3:
        comp2_url = st.text_input("競合B", placeholder="競合BのURL")
    submit_btn = st.form_submit_button("業界解読・診断開始")

if submit_btn and my_url and comp1_url:
    with st.spinner("サイト解析中..."):
        my_data = get_site_content(my_url)
        c1_data = get_site_content(comp1_url)
        c2_data = get_site_content(comp2_url) if comp2_url else ""

    # --- 診断実行 ---
    try:
        with st.spinner("シニアコンサルタントが思考中..."):
            # 賢い方のモデル「gpt-4o」に戻し、指示を「残酷なまでに具体的に」固定
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "あなたは一切の妥協を許さないシニアWebコンサルタントです。一般論や綺麗事は排除し、競合と比較して『何が決定的にダメか』を具体的・実務的な毒舌で指摘してください。"},
                    {"role": "user", "content": f"""
以下の3サイトを比較し、診断せよ。

【自社】: {my_data}
【競合A】: {c1_data}
【競合B】: {c2_data}

以下の構成で出力せよ：

■0. ポジショニング分析
・（特徴）/（競合比較）/（総合評価）を、Webキャラクター（親しみ型・権威型等）に触れて分析せよ。

■1. コンテンツの「網羅性と深さ」
・【Q&Aの専門性】【解決事例の具体性（時系列・金額等の一次情報）】【コラムの鮮度】の3点について、競合と比べて自社に足りない「生々しい情報」を指摘せよ。

■2. 成約導線と「顧客心理ハードル」
・【ファーストビューの即決力】【料金の透明性】【顔が見える安心感（写真の質など）】の3点について、自社がユーザーを逃している具体的要因を指摘せよ。

■3. EEAT（経験・専門性・権威性・信頼性）の診断
・【著者のプロフィール厚み】【公的リンク】【実績の客観的証明】について、GoogleやAIに評価されない致命的欠陥を暴け。

■4. SEO / LLMO（AI検索）適応状況
・【構造化ナレッジ】【セマンティック構造】【ゼロクリック検索対策】について改善点を特定せよ。

■5. 競合を圧倒する「新規コンテンツ案」10選
・（タイトル）（狙い）（具体的キーワード）をセットで。

■6. 戦略キーワード10選

■7. 最優先アクション（守りと攻め）
・【守り（即修正）】どのページの、どの要素をどう直すか3つ。
・【攻め（拡大）】どのキーワードで、どう集客するか2つ。

■8. リライト推奨ページと課題
・対象ページ名と、そこで解決すべき具体的課題のみを記せ。
"""}
                ],
                temperature=0.0
            )
            st.markdown(response.choices[0].message.content)
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
