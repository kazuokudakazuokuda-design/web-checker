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
                "1. 文体は「です・ます調」で統一してください。\n"
                "2. 競合に関してはテキストデータに基づく『客観的事実（有無や数）』のみを記述してください。\n"
                "3. 自社に関しては、事実に基づいた上で、経営・制作実務に直結する『戦略的な深掘り提言』を圧倒的な文章量（1項目500文字以上）で記述してください。\n"
                "4. 「不明」という逃げの表現は厳禁です。データにない場合は「記載がない」と断定した上で、自社の場合はそのリスクや補完策を論じてください。\n"
                "5. デザインの感想など視覚的ハルシネーションは禁止。テキストの語彙と構造のみで分析してください。"
            )
            
            user_msg = (
                f"【対象業界】: {st.session_state.industry}\n"
                f"【自社テキスト】: {st.session_state.my_res['content']}\n"
                f"【競合Aテキスト】: {st.session_state.c1_res['content']}\n"
                f"【競合Bテキスト】: {st.session_state.c2_res['content']}\n"
                f"【各サイト Description】: 自社:{st.session_state.my_res['description']} / A:{st.session_state.c1_res['description']} / B:{st.session_state.c2_res['description']}\n\n"
                "以下の構成で、制作会社の社長が現場への指示にそのまま使える濃厚なレポートを作成してください。\n\n"
                "### ■ 診断対象\n"
                f"- 自社: {st.session_state.urls['my']}\n"
                f"- 競合A: {st.session_state.urls['c1']}\n"
                f"- 競合B: {st.session_state.urls['c2']}\n\n"
                "### ■ 各サイトのメタ・ディスクリプション（事実のみ）\n\n"
                "### ■ 業界Web戦略基準の定義（5大基準）\n\n"
                "### ■1. 実績の透明性と「実務解像度」の分析\n"
                "- 【競合の事実】: 競合A・Bが提示している数字、事例、具体的名称の有無を列挙。\n"
                "- 【自社への深掘り提言】: 自社の実績記述が顧客の『投資対効果への不安』を払拭できているか診断し、信頼を勝ち取るための具体的追記案を詳述してください。\n\n"
                "### ■2. 成約導線とスマホUXの構造診断\n"
                "- 【事実比較】: 問い合わせボタン周辺のマイクロコピー（安心させる一言）の有無、1文の長さや箇条書きの活用度を比較。\n"
                "- 【自社への深掘り提言】: 現在のテキスト構造がスマホユーザーに与える『心理的負荷』を分析。離脱を防ぎ、成約ハードルを下げるためのリライト案を提言してください。\n\n"
                "### ■3. EEAT 診断（経験・専門性・権威性・信頼性）\n"
                "- 【競合の事実】: 各要素の具体的キーワード、資格、所属、独自ナレッジの有無を列挙。\n"
                "- 【自社への深掘り提言】: 競合に負けている要素を特定し、自社の持つどの潜在的知見をコンテンツ化すれば逆転できるか、戦略的なコンテンツ制作指針を詳述してください。\n\n"
                "### ■4. SEO / LLMO と情報の鮮度分析\n"
                "- 【事実比較】: 過去3ヶ月以内の更新数と具体的トピック名を各社分抽出。\n"
                "- 【自社への深掘り提言】: 更新頻度が『保守・運用の信頼感』に与えるリスク/メリットを分析。不足している専門用語5個を指摘し、AI検索時代に生き残るためのワード戦略を詳述してください。\n\n"
                "### ■5. 自社が勝つための戦略的コンテンツ案 5案\n\n"
                "### ■6. 最優先アクションプラン（自社用）\n"
                "- 【最優先】（2案）/ 【優先】（2案） / 【次の課題】（2案）\n"
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
