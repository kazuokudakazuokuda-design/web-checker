import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import streamlit.components.v1 as components
import re

# 1. 画面構成
st.set_page_config(page_title="🛡️ 戦略Web診断：事実と示唆", layout="wide")
st.title("🛡️ 戦略的Web比較診断レポート")
st.caption("※入力URLの物理数値から、経営リスク（示唆）と具体的修正タスクを生成します。")

# --- 設定エリア ---
st.divider()
st.subheader("🔍 解析対象の設定")
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
        avg_p_len = int(total_chars / len(p_tags)) if len(p_tags) > 0 else 0
        
        nums = len(re.findall(r'\d+', text_content))
        metrics = {
            "unique_links": unique_internal_links, "h_count": len(h_tags), "a_count": len(links),
            "img_count": len(img_tags), "alt_missing": alt_missing, "avg_p_len": avg_p_len,
            "num_count": nums, "text": text_content[:8000] 
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
        navigator.clipboard.writeText(text).then(() => {{ alert("レポートをコピーしました！"); }});
    }}
    </script>
    <button onclick="copyText()" style="
        background-color: #4CAF50; color: white; border: none; padding: 12px 24px;
        border-radius: 4px; cursor: pointer; font-weight: bold; width: 100%; margin-bottom: 20px;
    ">📋 レポートをコピーする</button>
    """
    return components.html(js_code, height=70)

if 'step' not in st.session_state:
    st.session_state.step = 1
    st.session_state.industry = ""

if st.button("STEP 1: 業界解析"):
    if not my_url or not comp1_url:
        st.error("自社と競合AのURLは必須です。")
    else:
        with st.spinner("診断中"):
            st.session_state.my_m = get_site_metrics(my_url)
            st.session_state.c1_m = get_site_metrics(comp1_url)
            st.session_state.c2_m = get_site_metrics(comp2_url) if comp2_url else None
            
            if st.session_state.my_m and st.session_state.c1_m:
                ind_prompt = f"このWebサイトの業界名のみを1語で回答してください。\n\nテキスト:{st.session_state.my_m['text'][:2000]}"
                response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": ind_prompt}], temperature=0.0)
                st.session_state.industry = response.choices[0].message.content
                st.session_state.step = 2

if st.session_state.step >= 2:
    st.divider()
    industry_input = st.text_input("解析対象の業界", value=st.session_state.industry)
    
    if st.button("STEP 2: 具体的戦略レポートを生成"):
        st.session_state.industry = industry_input
        with st.spinner("診断中"):
            def fmt_m(m):
                if not m: return "なし"
                return f"ページ:{m['unique_links']}, 見出し:{m['h_count']}, リンク:{m['a_count']}, 画像:{m['img_count']}(Alt欠:{m['alt_missing']}), 段落:{m['avg_p_len']}字, 数値出現:{m['num_count']}"
            m_data = f"自社: {fmt_m(st.session_state.my_m)}\n競合A: {fmt_m(st.session_state.c1_m)}\n"
            if st.session_state.c2_m: m_data += f"競合B: {fmt_m(st.session_state.c2_m)}\n"

            sys_msg = (
                f"あなたは{st.session_state.industry}業界のWeb戦略の鬼です。丁寧な『ですます調』でレポートを作成してください。\n\n"
                "【記述の絶対ルール】\n"
                "1. **見出しに（表形式）等のメタ説明を一切書かないこと。**\n"
                "2. 各項目は必ず『事実：』と『示唆：』に分けること。\n"
                "3. 『事実：』には計測数値と、自社テキストから抽出した具体的な不備（例：〇〇の具体的解説が皆無である、等）を特定して書くこと。\n"
                "4. 『示唆：』には数値の格差（構造的欠陥）が、業界の顧客心理においていかに致命的な損失（信頼喪失、離脱、商機逸失）を招いているかをえぐり、[どのページのどの箇所]を[具体的にどう直すか]を名指しで命令すること。\n"
                "5. **段落長の判定**：自社が100字超なら「スマホでの文字の壁」であり、短文化・箇条書きへの解体を命じるのが正解です。競合が長くても絶対に追随させないこと。\n"
                "6. **2x3アクションプラン**：最優先・優先・次のステップ各2項目。具体的な修正ページと具体的文言をピンポイントで指定すること。"
            )
            user_msg = f"業界: {st.session_state.industry}\nデータ:\n{m_data}\n自社テキスト抜粋: {st.session_state.my_m['text'][:4500]}\n\n### ■ 物理構造スペック比較\n### ■1. コンテンツの実務解像度分析\n#### 【実績の裏付け（証拠の密度）】\n### ■2. 成約導線とスマホUXの物理解析\n#### 【CTAとマイクロコピー】\n#### 【テキスト構造と可読性】\n### ■3. EEAT 診断（情報の権威性と信頼性）\n#### 【専門性（Expertise）】\n#### 【権威性（Authoritativeness）】\n#### 【信頼性（Trustworthiness）】\n### ■4. SEO / LLMO 診断（構造と鮮度）\n#### 【内部構造（見出し・リンク）】\n#### 【サイト構造（階層・網羅性）】\n#### 【情報の鮮度と生存確認】\n### ■5. 自社が勝つための具体的戦略案 5案\n### ■6. 最優先改善アクションプラン（自社用）"
            
            diag_res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}], temperature=0.0)
            st.session_state.full_report = diag_res.choices[0].message.content

    if st.session_state.get("full_report"):
        st.divider()
        st.markdown(st.session_state.full_report)
        copy_to_clipboard_js(st.session_state.full_report)
