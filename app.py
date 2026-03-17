import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# 1. 画面構成とAPIキーの設定
st.set_page_config(page_title="🛡️ 戦略・実務診断レポート", layout="wide")
st.title("🛡️ 実務特化型 Web戦略診断")
st.caption("AIが業界の成功法則を解読し、競合との格差を徹底診断します")

# StreamlitのSecretsからAPIキーを自動読み込み
try:
    raw_key = st.secrets["OPENAI_API_KEY"]
    # 前後の空白や引用符を徹底的に掃除してエラーを防ぐ
    api_key = raw_key.strip().strip('"').strip("'").replace(' ', '').replace('　', '')
    client = OpenAI(api_key=api_key)
except Exception as e:
    st.error(f"APIキーの読み込みに失敗しました。Secretsの設定を確認してください。")
    st.stop()

def get_site_content(url):
    """サイトの文字情報を拾ってくる関数（文字数制限を強化）"""
    try:
        url = url.strip()
        if not url.startswith("http"): url = "https://" + url
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, "html.parser")
        for s in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            s.decompose()
        elements = soup.find_all(["title", "h1", "h2", "h3", "p", "li"])
        content = "\n".join([e.get_text().strip() for e in elements if e.get_text().strip()])
        # AIがパンクしないよう、各サイト3000文字までに制限
        return content[:3000] 
    except Exception as e:
        return f"取得失敗: {str(e)}"

# 2. URLの入力フォーム
with st.form("input_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        my_url = st.text_input("自社サイトURL", placeholder="https://example.com")
    with col2:
        comp1_url = st.text_input("競合サイトA URL", placeholder="https://comp-a.com")
    with col3:
        comp2_url = st.text_input("競合サイトB URL", placeholder="https://comp-b.com")
    
    submit_btn = st.form_submit_button("業界解読・診断開始")

if submit_btn and my_url and comp1_url and comp2_url:
    with st.spinner("サイト群から情報を収集中..."):
        my_data = get_site_content(my_url)
        c1_data = get_site_content(comp1_url)
        c2_data = get_site_content(comp2_url)
        
        # 【デバッグ】もしデータが取れていなければ警告
        if len(my_data) < 50:
            st.warning(f"自社サイトの内容が十分に取得できていません（{len(my_data)}文字）。URLが正しいか、ブロックされていないか確認してください。")

    # --- PHASE 1: 業界基準の生成 ---
    try:
        # 安定性の高い gpt-4o-mini を使用
        res_phase1 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"以下のサイト情報から戦略基準を5つ定義せよ。\n自社:{my_data}\n競合A:{c1_data}\n競合B:{c2_data}"}],
            temperature=0.0
        )
        industry_standards = res_phase1.choices[0].message.content
        st.success("STEP 1: 成功法則の解読完了")
        st.markdown(industry_standards)

        st.divider()

        # --- PHASE 2: 詳細診断レポート ---
        with st.spinner("詳細レポートを生成中..."):
            phase2_prompt = f"""
            以下の基準に基づき、自社サイトと競合を比較して診断せよ。
            「情報不足」と言い訳せず、推測を交えて冷徹に指摘すること。
            【基準】: {industry_standards}
            【データ】自社:{my_data} / 競合A:{c1_data} / 競合B:{c2_data}
            
            構成：
            ■0. ポジショニング分析
            ■1. コンテンツの「網羅性と深さ」
            ■2. 成約導線と「顧客心理ハードル」
            ■3. EEAT診断
            ■4. SEO / LLMO適応状況
            ■5. 新規コンテンツ案10選
            ■6. 戦略キーワード10選
            ■7. 最優先アクション（守り・攻め）
            ■8. リライト推奨ページと課題
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "あなたは冷徹なコンサルタントです。"}, {"role": "user", "content": phase2_prompt}],
                temperature=0.0
            )
            st.header("🛡️ 戦略・実務診断レポート")
            st.markdown(response.choices[0].message.content)

    except Exception as e:
        # BadRequestErrorなどの具体的な原因を表示
        st.error(f"OpenAI APIエラーが発生しました: {e}")
