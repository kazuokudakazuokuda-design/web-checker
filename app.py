import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import streamlit.components.v1 as components

# 1. 画面構成
st.set_page_config(page_title="🛡️ 業界特化型 Web戦略診断", layout="wide")
st.title("🛡️ 業界特化型 Web戦略診断")
st.caption("※生成AIによる一次診断です。自社の戦略立案のヒントとしてご活用ください。")

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
        
        # Meta Description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        description = meta_desc["content"].strip() if meta_desc else "未設定"
        
        # 本文テキスト抽出
        for s in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            s.decompose()
        lines = []
        for tag in soup.find_all(['title', 'h1', 'h2', 'h3', 'h4', 'p', 'li', 'dt', 'dd', 'table']):
            text = tag.get_text().strip()
            if len(text) > 2:
                lines.append(f"<{tag.name}>{text}")
        content = "\n".join(lines)[:8500]
        
        return {"description": description, "content": content}
    except Exception as e:
        return {"description": "取得エラー", "content": "データ取得エラー"}

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
            with st.spinner("業界を解析中..."):
                st.session_state.my_res = get_site_content(my_url)
                st.session_state.c1_res = get_site_content(comp1_url)
                st.session_state.c2_res = get_site_content(comp2_url) if comp2_url else {"description": "なし", "content": "なし"}
                st.session_state.urls = {"my": my_url, "c1": comp1_url, "c2": comp2_url if comp2_url else "-"}
                
                ind_prompt = f"業界名を回答せよ。余計な言葉は不要。\n\n自社:{st.session_state.my_res['content']}\n競合:{st.session_state.c1_res['content']}"
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": ind_prompt}],
                    temperature=0.0
                )
                st.session_state.industry = response.choices[0].message.content.replace("業界", "")
                st.session_state.step = 2

if st.session_state.step >= 2:
    st.subheader("📌 業界確認と詳細診断の実行")
    industry_input = st.text_input("特定された業界", value=st.session_state.industry)
    
    if st.button("診断を開始する"):
        st.session_state.industry = industry_input
        with st.spinner("プロフェッショナル戦略診断を実行中..."):
            sys_msg = (
                "あなたは超一流のWebストラテジストです。\n"
                "1. すべての主要項目において、指定された『小分類』の見出しを必ず作成してください。\n"
                "2. 各小分類の中で、必ず『競合の事実（テキストデータに基づく有無や数）』と『自社への戦略的深掘り提言』を対比させて記述してください。\n"
                "3. 自社への深掘り提言は、社長が現場にそのまま指示を出せるレベルの濃厚な文章量（各小項目500文字程度）で記述してください。\n"
                "4. 「不明」「わからない」という逃げは厳禁。記載がない場合は「記載がない」と断定し、自社の場合はその欠落が招くリスクと改善策を具体的に詳述してください。\n"
                "5. 視覚的推測は禁止。テキストの語彙とタグ構造のみで分析してください。"
            )
            
            user_msg = (
                f"【対象業界】: {st.session_state.industry}\n"
                f"【自社テキスト】: {st.session_state.my_res['content']}\n"
                f"【競合Aテキスト】: {st.session_state.c1_res['content']}\n"
                f"【競合Bテキスト】: {st.session_state.c2_res['content']}\n"
                f"【各サイト Description】: 自社:{st.session_state.my_res['description']} / A:{st.session_state.c1_res['description']} / B:{st.session_state.c2_res['description']}\n\n"
                "制作会社の社長に提出する、現場指示書レベルの超詳細レポートを作成してください。\n\n"
                "### ■1. コンテンツの実務解像度分析\n"
                "#### 【実績の裏付け（証拠の密度）】\n"
                "競合の具体的数値・事例名の有無と、自社が2000社の実績をどう戦略的に見せ直すべきか深掘り。\n"
                "#### 【提供価値の具体的証明（ロジック）】\n"
                "競合の課題解決フローの有無と、自社の独自プロセスをどう言語化すべきか深掘り。\n\n"
                "### ■2. 成約導線とスマホUXの物理解析\n"
                "#### 【CTAとマイクロコピー】\n"
                "問い合わせ周辺の文言比較と、自社が成約ハードルを下げるための具体的文言案を深掘り。\n"
                "#### 【テキスト構造と可読性】\n"
                "1文の長さや箇条書き活用度による離脱リスク比較と、自社のリライト方針を深掘り。\n\n"
                "### ■3. EEAT 診断（情報の権威性と信頼性）\n"
                "#### 【経験（Experience）】\n"
                "独自の工程や工夫の記述比較と、自社の知見をどう1次情報化すべきか深掘り。\n"
                "#### 【専門性（Expertise）】\n"
                "技術解説の解像度比較と、自社が勝つための専門コンテンツ制作戦略を深掘り。\n"
                "#### 【権威性（Authoritativeness）】\n"
                "公的証明や固有名詞の有無と、自社の権威付けをどう強化すべきか深掘り。\n"
                "#### 【信頼性（Trustworthiness）】\n"
                "透明性の事実比較と、自社が顧客の『最後の一押し』を勝ち取るための改善案を深掘り。\n\n"
                "### ■4. SEO / LLMO と情報の鮮度分析\n"
                "#### 【情報の鮮度（Freshness）】\n"
                "過去3ヶ月の更新数・トピック名の事実比較と、自社の更新頻度が信頼に与える影響を深掘り。\n"
                "#### 【インテント適合度とセマンティック・ギャップ】\n"
                "Description整合性比較と、自社に不足する専門用語5個を軸にしたワード戦略を深掘り。\n\n"
                "### ■5. 自社が勝つための戦略的コンテンツ案 5案\n"
                "### ■6. 最優先改善アクションプラン（自社用）"
            )
            
            diag_res = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}],
                temperature=0.0
            )
            st.session_state.full_report = diag_res.choices[0].message.content
            st.session_state.step = 3

if st.session_state.step >= 3:
    st.divider()
    st.markdown("## 🛡️ 戦略・実務詳細診断レポート")
    st.markdown(st.session_state.full_report)
    st.divider()
    st.subheader("📋 レポートをコピーする")
    copy_to_clipboard_js(st.session_state.full_report)
