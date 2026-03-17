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
                "以下の記述ルールを厳守してください。\n"
                "1. 文章は短く切ってください。「〜ですが、」「〜であり、」といった接続助詞による長文を禁止します。\n"
                "2. 項目名と本文の間には必ず改行を入れてください。\n"
                "3. 競合に関してはテキストデータに基づく『客観的事実』のみを端的に記述してください。\n"
                "4. 自社に関しては、事実に基づいた『戦略的な深掘り提言』を圧倒的な文章量で記述してください。社長へのアドバイスとして断定的に書いてください。\n"
                "5. 「不明」は厳禁です。データにない場合は「記載がない」と断定し、自社の場合はそのリスクを論じてください。\n"
                "6. デザインの感想など視覚的推測は禁止。タグ構造とテキストのみで分析してください。"
            )
            
            user_msg = (
                f"【対象業界】: {st.session_state.industry}\n"
                f"【自社テキスト】: {st.session_state.my_res['content']}\n"
                f"【競合Aテキスト】: {st.session_state.c1_res['content']}\n"
                f"【競合Bテキスト】: {st.session_state.c2_res['content']}\n"
                f"【各サイト Description】: 自社:{st.session_state.my_res['description']} / A:{st.session_state.c1_res['description']} / B:{st.session_state.c2_res['description']}\n\n"
                "制作会社の社長に提出する、現場指示書レベルのレポートを作成してください。\n\n"
                "### ■1. コンテンツの実務解像度分析\n"
                "#### 【実績の裏付け（証拠の密度）】\n"
                "競合の具体的数値・事例名の有無と、自社が持つ実績の山をどう戦略的に見せ直すべきか提言してください。\n"
                "#### 【提供価値の具体的証明（ロジック）】\n"
                "競合の課題解決フローの有無と、自社の独自プロセスをどう言語化すべきか提言してください。\n\n"
                "### ■2. 成約導線とスマホUXの物理解析\n"
                "#### 【CTAとマイクロコピー】\n"
                "ボタン周辺の安心させる文言の有無を比較。自社の成約ハードルを下げるための具体的文言を提言してください。\n"
                "#### 【テキスト構造と可読性】\n"
                "1文の長さや箇条書き活用度による離脱リスクを比較。自社のリライト方針を提言してください。\n\n"
                "### ■3. EEAT 診断\n"
                "#### 【経験（Experience）】\n"
                "独自の工程や工夫の記述を比較。自社の知見をどう1次情報化すべきか提言してください。\n"
                "#### 【専門性（Expertise）】\n"
                "技術解説の解像度を比較。自社が勝つための専門コンテンツ制作戦略を提言してください。\n"
                "#### 【権威性（Authoritativeness）】\n"
                "公的証明や固有名詞の有無を比較。自社の権威付けをどう強化すべきか提言してください。\n"
                "#### 【信頼性（Trustworthiness）】\n"
                "透明性の事実比較。自社が顧客の『最後の一押し』を勝ち取るための改善案を提言してください。\n\n"
                "### ■4. SEO / LLMO 診断\n"
                "#### 【内部構造（見出し・リンク）】\n"
                "見出しタグの論理性と内部リンクのアンカーテキストの適切性を診断し、自社への改善案を提言してください。\n"
                "#### 【サイト構造（階層・網羅性）】\n"
                "クリック階層の深さやページのカニバリ有無を診断し、自社のサイトマップ整理案を提言してください。\n"
                "#### 【表示速度への構造的配慮】\n"
                "WebP対応やLazy Load等の技術的配慮の有無をタグから判定。自社が技術力で信頼を得るための提言をしてください。\n"
                "#### 【情報の鮮度（Freshness）】\n"
                "過去3ヶ月の更新数・トピック名の事実比較。自社の更新頻度が信頼に与える影響を提言してください。\n"
                "#### 【インテント適合度とセマンティック・ギャップ】\n"
                "Description整合性比較。自社に不足する専門用語5個を軸にしたワード戦略を提言してください。\n\n"
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
