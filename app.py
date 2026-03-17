import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import streamlit.components.v1 as components
import re

# 1. 画面構成
st.set_page_config(page_title="🛡️ 実務直結型・Web戦略診断", layout="wide")
st.title("🛡️ 実務直結型・Web戦略診断")
st.caption("※物理数値の格差から、現場への『具体的な改善命令』を導き出します。")

# --- 入力エリア ---
st.divider()
st.subheader("🔍 診断対象の設定")
col_u1, col_u2, col_u3 = st.columns(3)

with col_u1:
    my_url = st.text_input("自社URL", placeholder="https://example.com")
with col_u2:
    comp1_url = st.text_input("競合A", placeholder="https://competitor-a.com")
with col_u3:
    comp2_url = st.text_input("競合B（任意）", placeholder="https://competitor-b.com")

# API設定
try:
    api_key = st.secrets["OPENAI_API_KEY"].strip().strip('"')
    client = OpenAI(api_key=api_key)
except:
    st.error("APIキーの設定を確認してください。")
    st.stop()

def get_site_metrics(url):
    try:
        url = url.strip()
        if not url.startswith("http"): url = "https://" + url
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, "html.parser")
        
        for s in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            s.decompose()

        links = soup.find_all('a', href=True)
        domain = url.split("//")[-1].split("/")[0]
        internal_links = [l for l in links if domain in l['href'] or l['href'].startswith('/')]
        unique_internal_links = len(set([l['href'] for l in internal_links]))
        
        h_tags = soup.find_all(['h1', 'h2', 'h3', 'h4'])
        p_tags = soup.find_all('p')
        img_tags = soup.find_all('img')
        alt_missing = len([img for img in img_tags if not img.get('alt') or img.get('alt').strip() == ""])
        
        text_content = soup.get_text()
        total_chars = len(text_content.strip())
        avg_p_len = total_chars / len(p_tags) if len(p_tags) > 0 else 0
        
        nums = len(re.findall(r'\d+', text_content))
        has_faq = any(k in text_content for k in ["よくある質問", "FAQ", "Q&A", "疑問"])
        has_service = any(k in text_content for k in ["サービス", "案内", "メニュー", "料金"])

        metrics = {
            "unique_links": unique_internal_links,
            "h_count": len(h_tags),
            "a_count": len(links),
            "img_count": len(img_tags),
            "alt_missing": alt_missing,
            "avg_p_len": int(avg_p_len),
            "num_count": nums,
            "has_faq": "あり" if has_faq else "なし",
            "has_service": "あり" if has_service else "なし",
            "text": text_content[:8000] 
        }
        return metrics
    except:
        return None

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

if st.button("STEP 1: サイト情報を解析"):
    if not my_url or not comp1_url:
        st.error("URLを入力してください。")
    else:
        with st.spinner("診断中"):
            st.session_state.my_m = get_site_metrics(my_url)
            st.session_state.c1_m = get_site_metrics(comp1_url)
            st.session_state.c2_m = get_site_metrics(comp2_url) if comp2_url else None
            
            if st.session_state.my_m and st.session_state.c1_m:
                ind_prompt = f"業界名を回答してください。余計な言葉は不要です。\n\nテキスト:{st.session_state.my_m['text'][:2000]}"
                response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": ind_prompt}], temperature=0.0)
                st.session_state.industry = response.choices[0].message.content.replace("業界", "")
                st.session_state.step = 2

if st.session_state.step >= 2:
    st.divider()
    st.subheader("📌 具体的戦略レポート生成")
    industry_input = st.text_input("解析業界", value=st.session_state.industry)
    
    if st.button("STEP 2: 診断レポート生成"):
        st.session_state.industry = industry_input
        with st.spinner("診断中"):
            
            def fmt_m(m):
                if not m: return "データなし"
                return (f"推定ページ数:{m['unique_links']}, 見出し数:{m['h_count']}, リンク総数:{m['a_count']}, "
                        f"画像数:{m['img_count']}(Alt欠落:{m['alt_missing']}), 段落長:{m['avg_p_len']}字, "
                        f"数値/固有名詞出現数:{m['num_count']}, FAQ:{m['has_faq']}, 案内:{m['has_service']}")

            m_data = f"自社: {fmt_m(st.session_state.my_m)}\n競合A: {fmt_m(st.session_state.c1_m)}\n"
            if st.session_state.c2_m: m_data += f"競合B: {fmt_m(st.session_state.c2_m)}\n"

            sys_msg = (
                f"あなたは{st.session_state.industry}業界のWeb戦略の鬼と呼ばれる専門家です。\n"
                "丁寧な『ですます調』を用いつつ、一般論を一切排した『実務上の急務』を突きつけるレポートを作成してください。\n\n"
                "【出力の絶対ルール】\n"
                "1. **『示唆：』の解像度を最大化せよ**：\n"
                "   - 『〜すべきです』で終わらせず、『自社の〇〇という数値は、競合と比較して実務上の△△という機会損失を招いている。具体的に、[どのページ]の[どの見出し]を、[どのような実務用語]を用いてリライト・分割せよ』と具体的に指示してください。\n"
                "2. **実務用語の強制使用**：『最新事例』等の汎用ワードは禁止。業界に即した具体的名称（例：求人票リライト実績、成約率改善データ等）を使用してください。\n"
                "3. **鮮度のリスク指摘**：更新日が不明であることに対し、放置されている恐怖（顧客が『この会社は動いていない』と判断する心理的損失）を具体的に綴ってください。\n"
                "4. **2x3アクションプラン**：最優先・優先・次のステップの各時間軸で2つずつ、『どのページのどの箇所をいじるか』を指定したタスクを提示してください。"
            )
            
            user_msg = (
                f"業界: {st.session_state.industry}\n"
                f"物理数値データ:\n{m_data}\n"
                f"自社テキスト抜粋: {st.session_state.my_m['text'][:4500]}\n\n"
                "以下の構成で作成してください：\n\n"
                "### ■ 物理構造スペック比較（表形式）\n"
                "### ■1. コンテンツの実務解像度分析\n"
                "#### 【実績の裏付け（証拠の密度）】\n"
                "### ■2. 成約導線とスマホUXの物理解析\n"
                "#### 【CTAとマイクロコピー】\n"
                "#### 【テキスト構造と可読性】\n"
                "### ■3. EEAT 診断（情報の権威性と信頼性）\n"
                "#### 【専門性（Expertise）】\n"
                "#### 【権威性（Authoritativeness）】\n"
                "#### 【信頼性（Trustworthiness）】\n"
                "### ■4. SEO / LLMO 診断（構造と鮮度）\n"
                "#### 【内部構造（見出し・リンク）】\n"
                "#### 【サイト構造（階層・網羅性）】\n"
                "#### 【情報の鮮度と生存確認】\n\n"
                "### ■5. 自社が勝つための具体的コンテンツ企画 5案\n"
                "### ■6. 最優先改善アクションプラン（自社用）\n"
                "（最優先・優先・次ステップの2x3形式で、修正ページや箇所をピンポイント指定すること）"
            )
            
            diag_res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}], temperature=0.0)
            st.session_state.full_report = diag_res.choices[0].message.content
            st.session_state.step = 3

if st.session_state.step >= 3:
    st.divider()
    st.markdown(st.session_state.full_report)
    copy_to_clipboard_js(st.session_state.full_report)
