import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import streamlit.components.v1 as components
import re

# 1. 画面構成
st.set_page_config(page_title="🛡️ 戦略Web診断：実務命令版", layout="wide")
st.title("🛡️ 経営直結型・Web戦略診断")
st.caption("※物理数値と業界慣習から「現場が動かざるを得ない修正タスク」を生成します。")

# --- 設定エリア ---
st.divider()
st.subheader("🔍 解析対象の設定")
col_u1, col_u2, col_u3 = st.columns(3)

with col_u1:
    my_url = st.text_input("自社URL", value="https://akagaki-dental.com/")
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
        st.error("URLを入力してください。")
    else:
        with st.spinner("診断中"):
            st.session_state.my_m = get_site_metrics(my_url)
            st.session_state.c1_m = get_site_metrics(comp1_url)
            st.session_state.c2_m = get_site_metrics(comp2_url) if comp2_url else None
            
            if st.session_state.my_m and st.session_state.c1_m:
                ind_prompt = f"業界名のみを1語で回答せよ。\n\nテキスト:{st.session_state.my_m['text'][:2000]}"
                response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": ind_prompt}], temperature=0.0)
                st.session_state.industry = response.choices[0].message.content
                st.session_state.step = 2

if st.session_state.step >= 2:
    st.divider()
    industry_input = st.text_input("解析業界ベース", value=st.session_state.industry)
    
    if st.button("STEP 2: 具体的戦略レポート生成"):
        st.session_state.industry = industry_input
        with st.spinner("診断中"):
            def fmt_m(m):
                if not m: return "なし"
                return f"ページ:{m['unique_links']}, 見出し:{m['h_count']}, リンク:{m['a_count']}, 画像:{m['img_count']}(Alt欠:{m['alt_missing']}), 段落:{m['avg_p_len']}字, 数値出現:{m['num_count']}"
            m_data = f"自社: {fmt_m(st.session_state.my_m)}\n競合A: {fmt_m(st.session_state.c1_m)}\n"
            if st.session_state.c2_m: m_data += f"競合B: {fmt_m(st.session_state.c2_m)}\n"

            sys_msg = (
                f"あなたは{st.session_state.industry}業界のWeb戦略の鬼です。丁寧な『ですます調』で、社長が即決できる具体的で厳しいレポートを作成してください。\n\n"
                "【出力の絶対ルール】\n"
                "1. **数値の罪を数えよ**：『見出しが〇個少ない』事実に対し、『これはユーザーの△△という悩みを無視している証拠だ』と断定してください。\n"
                "2. **『示唆：』の解像度**：一般論を禁止します。『自社サイトの[ページ名]にある[見出し]を、[業界の具体的悩み]を解決する文言に書き換え、情報を分割せよ』と名指しで指示してください。\n"
                "3. **スマホUXの正答**：段落100字超は『不快な壁』です。短文化と箇条書きへの解体を命じてください。\n"
                "4. **鮮度のリスク**：更新日不明を『患者/顧客が廃業を疑う致命的欠陥』としてえぐり、即座に2026年3月の日付を含むコンテンツを投稿するよう命じてください。\n"
                "5. **2x3アクションプラン**：最優先・優先・次のステップ各2項目。具体的な修正箇所（例：[院長紹介ページの中段]など）を指定すること。"
            )
            user_msg = f"業界: {st.session_state.industry}\nデータ:\n{m_data}\n自社テキスト: {st.session_state.my_m['text'][:5000]}\n\n### ■ 物理構造スペック比較\n### ■1. コンテンツの実務解像度分析\n#### 【実績の裏付け（証拠の密度）】\n### ■2. 成約導線とスマホUXの物理解析\n#### 【CTAとマイクロコピー】\n#### 【テキスト構造と可読性】\n### ■3. EEAT 診断（情報の権威性と信頼性）\n#### 【専門性（Expertise）】\n#### 【権威性（Authoritativeness）】\n#### 【信頼性（Trustworthiness）】\n### ■4. SEO / LLMO 診断（構造と鮮度）\n#### 【内部構造（見出し・リンク）】\n#### 【サイト構造（階層・網羅性）】\n#### 【情報の鮮度と生存確認】\n### ■5. 自社が勝つための具体的戦略案 5案\n### ■6. 最優先改善アクションプラン（自社用）"
            
            diag_res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}], temperature=0.0)
            st.session_state.full_report = diag_res.choices[0].message.content

    if st.session_state.get("full_report"):
        st.divider()
        st.markdown(st.session_state.full_report)
        copy_to_clipboard_js(st.session_state.full_report)
