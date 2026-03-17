import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import streamlit.components.v1 as components

# 1. 画面構成
st.set_page_config(page_title="🛡️ Web戦略・実装構造 比較診断", layout="wide")
st.title("🛡️ Web戦略・実装構造 比較診断")
st.caption("※生成AIによる分析です。実務上の最終判断は専門家と協議の上で行ってください。")

# API設定
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
        
        # Meta情報
        meta_desc = soup.find("meta", attrs={"name": "description"})
        description = meta_desc["content"].strip() if meta_desc else "未設定"
        
        # 本文テキスト（タグ構造を維持して抽出）
        for s in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            s.decompose()
        lines = []
        for tag in soup.find_all(['title', 'h1', 'h2', 'h3', 'h4', 'p', 'li', 'dt', 'dd', 'table', 'img']):
            if tag.name == 'img':
                # 画像の最適化（Lazyload/WebP）の判定用属性を擬似的にテキスト化
                lazy = "lazy-ok" if tag.get('loading') == 'lazy' else "lazy-ng"
                src = tag.get('src', '')
                webp = "webp-ok" if ".webp" in src.lower() else "webp-ng"
                lines.append(f"<img_spec>{lazy}_{webp}")
            else:
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
        background-color: #4CAF50; color: white; border: none; padding: 12px 24px;
        border-radius: 4px; cursor: pointer; font-weight: bold; width: 100%; margin-bottom: 20px;
    ">📋 レポートをコピーする（Markdown形式）</button>
    """
    return components.html(js_code, height=70)

if 'step' not in st.session_state:
    st.session_state.step = 1
    st.session_state.industry = ""
    st.session_state.full_report = ""

with st.sidebar:
    st.header("🔍 診断対象設定")
    my_url = st.text_input("自社URL", placeholder="https://example.com")
    comp1_url = st.text_input("競合A", placeholder="https://competitor-a.com")
    comp2_url = st.text_input("競合B", placeholder="（任意）")
    if st.button("STEP 1: サイト情報を解析"):
        if not my_url or not comp1_url:
            st.error("自社と競合AのURLは必須です。")
        else:
            with st.spinner("各サイトの構造を読み取っています..."):
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
    st.subheader("📌 診断の実行")
    industry_input = st.text_input("特定された業界", value=st.session_state.industry)
    
    if st.button("詳細レポートを生成"):
        st.session_state.industry = industry_input
        with st.spinner("戦略的な提言を構成しています..."):
            sys_msg = (
                "あなたは丁寧で論理的なWebストラテジストです。\n"
                "以下の記述ルールを徹底してください。\n"
                "1. 文章は短く切り、リズムを作ってください。「〜ですが、」「〜であり、」といった接続助詞による長文を禁止します。\n"
                "2. 項目名と本文の間には必ず改行を入れてください。\n"
                "3. 競合に関してはテキストデータに基づく『客観的事実』のみを端的に記述してください。\n"
                "4. 自社に関しては、事実に基づいた『戦略的な深掘り提言』を圧倒的な文章量で記述してください。礼節を保ちつつ、プロとしての改善策を断定的に書くこと。\n"
                "5. 煽りや不適切な暴言は厳禁。機会損失の解消や顧客信頼の向上という視点で論じてください。\n"
                "6. 「不明」は禁止。データにない場合は「記載がない」と断定し、自社の場合はその欠落が招くリスクと補完策を詳述してください。"
            )
            
            user_msg = (
                f"【対象業界】: {st.session_state.industry}\n"
                f"【自社URL】: {st.session_state.urls['my']}\n"
                f"【自社データ】: {st.session_state.my_res['content']}\n"
                f"【競合データ】: A:{st.session_state.c1_res['content']} / B:{st.session_state.c2_res['content']}\n\n"
                "以下の構成でレポートを作成してください。\n\n"
                "### ■1. コンテンツの実務解像度分析\n"
                "#### 【実績の裏付け（証拠の密度）】\n"
                "競合の具体的数値・事例名の有無と、自社実績を単なる数から『信頼の根拠』へ昇華させるための提言を記述。\n\n"
                "### ■2. 成約導線とスマホUXの物理解析\n"
                "#### 【CTAとマイクロコピー】\n"
                "ボタン周辺の安心させる文言の有無を比較。自社の成約ハードルを下げるための具体的文言案を提言。\n"
                "#### 【テキスト構造と可読性】\n"
                "1文の長さや箇条書き活用度による離脱リスク比較。自社のリライト方針を提言。\n\n"
                "### ■3. EEAT 診断（情報の権威性と信頼性）\n"
                "#### 【専門性（Expertise）】\n"
                "技術解説の解像度比較。自社が勝つための専門コンテンツ制作戦略を提言。\n"
                "#### 【権威性（Authoritativeness）】\n"
                "外部評価、業界団体、メディア実績等の有無を比較。自社の権威付けをどう強化すべきか（創業年数や特定知見の体系化など）を提言。\n\n"
                "### ■4. SEO / LLMO 診断\n"
                "#### 【内部構造（見出し・リンク）】\n"
                "見出しタグの具体性とアンカーテキスト（指示語の有無）を診断。自社への具体的な改善案を提言。\n"
                "#### 【サイト構造（階層・網羅性）】\n"
                "ディレクトリの深さやカニバリの有無を診断。重要なページへの到達性を高めるサイトマップ整理案を提言。\n"
                "#### 【表示速度への構造的配慮】\n"
                "WebP対応やLazy Load等の技術的配慮の有無を判定。自社が技術力で信頼を得るための実装改善を提言。\n"
                "#### 【情報の鮮度（Freshness）】\n"
                "過去3ヶ月の更新件数とトピック名の比較。更新頻度が対外的な信頼（生存確認）に与える影響を提言。\n\n"
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
    st.markdown("## 🛡️ Web戦略・実装構造 比較診断書")
    st.markdown(st.session_state.full_report)
    st.divider()
    st.subheader("📋 レポートを保存する")
    copy_to_clipboard_js(st.session_state.full_report)
