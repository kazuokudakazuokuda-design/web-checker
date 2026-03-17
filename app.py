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
        
        # Meta Descriptionの取得
        meta_desc = soup.find("meta", attrs={"name": "description"})
        description = meta_desc["content"].strip() if meta_desc else "未設定"
        
        # 本文テキストの抽出
        for s in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            s.decompose()
        lines = []
        for tag in soup.find_all(['title', 'h1', 'h2', 'h3', 'h4', 'p', 'li', 'dt', 'dd', 'table']):
            text = tag.get_text().strip()
            if len(text) > 2:
                lines.append(f"<{tag.name}>{text}")
        content = "\n".join(lines)[:8000]
        
        return {"description": description, "content": content}
    except Exception as e:
        return {"description": "取得エラー", "content": "データ取得エラー"}

# レポート一括コピー用JavaScript
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
                
                industry_prompt = f"業界名を回答せよ。余計な言葉は不要。\n\n自社:{st.session_state.my_res['content']}\n競合:{st.session_state.c1_res['content']}"
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": industry_prompt}],
                    temperature=0.0
                )
                st.session_state.industry = response.choices[0].message.content.replace("業界", "")
                st.session_state.step = 2

if st.session_state.step >= 2:
    st.subheader("📌 業界確認と詳細診断の実行")
    industry_input = st.text_input("特定された業界", value=st.session_state.industry)
    
    if st.button("診断を開始する"):
        st.session_state.industry = industry_input
        with st.spinner("全コンテンツを詳細診断中..."):
            # システムプロンプトとユーザープロンプトを整理
            sys_msg = (
                "あなたは丁寧かつ論理的、客観的な視点を持つ超一流のWebストラテジストです。\n"
                "1. 文体はすべて「です・ます調」で統一してください。\n"
                "2. 提供されたテキストデータに基づき「掲載されている」か「掲載されていない」かを明確に断定してください。「不明」「わからない」という逃げの表現は厳禁です。\n"
                "3. 各診断項目は、競合との格差がはっきりと伝わるよう、500文字以上の圧倒的な文章量で記述してください。\n"
                "4. 点数（〇〇点）の算出は一切行わないでください。\n"
                "5. 冒頭の「診断対象」以外には、本文中にURLやMarkdownリンクを一切記述しないでください。"
            )
            
            user_msg = (
                f"【対象業界】: {st.session_state.industry}\n"
                f"【自社テキスト】: {st.session_state.my_res['content']}\n"
                f"【競合Aテキスト】: {st.session_state.c1_res['content']}\n"
                f"【競合Bテキスト】: {st.session_state.c2_res['content']}\n"
                f"【各サイト Description】: 自社:{st.session_state.my_res['description']} / A:{st.session_state.c1_res['description']} / B:{st.session_state.c2_res['description']}\n\n"
                "上記データに基づき、以下の構成でレポートを作成してください。\n\n"
                "### ■ 診断対象\n"
                f"- 自社: {st.session_state.urls['my']}\n"
                f"- 競合A: {st.session_state.urls['c1']}\n"
                f"- 競合B: {st.session_state.urls['c2']}\n\n"
                "### ■ 各サイトのメタ・ディスクリプション（検索結果の説明文）\n"
                "（各サイトの設定内容を事実として列挙。未設定の場合は「未設定」と明記）\n\n"
                "### ■ 業界Web戦略基準の定義\n"
                "この業界で成約を勝ち取るために必須となる5大基準を、理由と評価ポイント（各3つ）を添えて詳細に出力してください。\n\n"
                "### ■0. 自社、競合のホームページの現状\n"
                "（※テキストから読み取れる情報の種類と構造のみを記述。評価はせず事実の整理に徹すること。冒頭以外はURL禁止。「不明」は禁止。記述がない場合は「〜の記載がない」と断定すること）\n\n"
                "### ■1. コンテンツの「実務解像度」の分析\n"
                "- 【実績の裏付け】: 具体的な数字や解決事例、プロジェクト名がテキスト内に存在するか。競合と比較してどちらが「具体的な事実」を提示できているか分析してください。\n"
                "- 【提供価値の具体的証明】: ユーザーの悩みを解決する論理的なステップが記述されているか。\n\n"
                "### ■2. 成約導線と「顧客心理ハードル」の分析\n"
                "- 【情報の優先順位】: ユーザーが求める結論（価格、事例等）が、テキスト構造上の上位にあるか。\n"
                "- 【プロセスの明快さ】: 問い合わせ後のフローが具体的に言語化されているか。\n\n"
                "### ■3. EEAT 診断\n"
                "※「不明」は厳禁。データの有無を断定してください。\n"
                "- 【経験（Experience）】: 独自の工程、工夫などの「一次情報」の記述があるか。\n"
                "- 【専門性（Expertise）】: 技術解説、実務フローの解像度。\n"
                "- 【権威性（Authoritativeness）】: 資格、所属団体、受賞歴等の具体的な固有名詞の記述があるか。\n"
                "- 【信頼性（Trustworthiness）】: 実名実績、更新頻度、運営者情報の詳細度。\n\n"
                "### ■4. SEO / LLMO 診断\n"
                "- 【インテント適合度と結論到達スピード】: Descriptionとコンテンツの整合性を分析。\n"
                "- 【サイテーション（外部言及）の状況】: 引用されるべき独自データやノウハウの記述があるか。\n"
                "- 【情報の鮮度（Freshness）】: 最終更新日、トレンドへの言及の有無。\n"
                "- 【セマンティック・ギャップ（専門用語5個）】: 自社に不足している重要用語を5個厳選し最後に解説してください。\n\n"
                "### ■5. 診断に基づく新規コンテンツ案 5案\n\n"
                "### ■6. 最優先改善アクションプラン\n"
                "- 【最優先】（2案）\n"
                "- 【優先】（2案）\n"
                "- 【次の課題】（2案）\n"
            )
            
            diag_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.0
            )
            st.session_state.full_report = diag_response.choices[0].message.content
            st.session_state.step = 3

if st.session_state.step >= 3:
    st.divider()
    st.markdown("## 🛡️ 戦略・実務詳細診断レポート")
    st.markdown(st.session_state.full_report)
    st.caption("※あくまで生成AIによる一次診断としてご利用ください。")
    st.divider()
    st.subheader("📋 レポートをコピーする")
    copy_to_clipboard_js(st.session_state.full_report)
