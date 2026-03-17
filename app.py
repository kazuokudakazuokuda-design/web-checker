import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import streamlit.components.v1 as components
import re

# 1. 画面構成
st.set_page_config(page_title="🛡️ 業界特化型Webサイト診断", layout="wide")
st.title("🛡️ 業界特化型Webサイト診断")
st.caption("※物理構造数値とEEAT・SEO戦略の統合分析。事実と示唆を分離したプロ仕様のレポート。")

# --- メインエリアに入力エリアを配置（スマホ配慮） ---
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

        # --- 物理数値の計測 ---
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
        has_service = any(k in text_content for k in ["サービス", "業務一覧", "メニュー", "料金"])

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
            "text": text_content[:7500] 
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
        st.error("自社と競合AのURLは必須です。")
    else:
        with st.spinner("物理構造とコンテンツを精密解析中..."):
            st.session_state.my_m = get_site_metrics(my_url)
            st.session_state.c1_m = get_site_metrics(comp1_url)
            st.session_state.c2_m = get_site_metrics(comp2_url) if comp2_url else None
            st.session_state.urls = {"my": my_url, "c1": comp1_url, "c2": comp2_url if comp2_url else "-"}
            
            ind_prompt = f"業界名を回答せよ。余計な言葉は不要。\n\nテキスト:{st.session_state.my_m['text']}"
            response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": ind_prompt}], temperature=0.0)
            st.session_state.industry = response.choices[0].message.content.replace("業界", "")
            st.session_state.step = 2

if st.session_state.step >= 2:
    st.divider()
    st.subheader("📌 戦略診断の実行")
    industry_input = st.text_input("特定された業界", value=st.session_state.industry)
    
    if st.button("STEP 2: 詳細診断レポートを生成"):
        st.session_state.industry = industry_input
        with st.spinner("「事実」と「示唆」を分離したレポートを構築中..."):
            
            def fmt_m(m):
                if not m: return "データなし"
                return (f"推定ページ数:{m['unique_links']}, 見出し数:{m['h_count']}, リンク総数:{m['a_count']}, "
                        f"画像数:{m['img_count']}(Alt欠落:{m['alt_missing']}), 平均段落長:{m['avg_p_len']}字, "
                        f"数値/固有名詞出現数:{m['num_count']}, FAQ:{m['has_faq']}, サービス案内:{m['has_service']}")

            m_data = f"【物理数値エビデンス】\n自社: {fmt_m(st.session_state.my_m)}\n競合A: {fmt_m(st.session_state.c1_m)}\n"
            if st.session_state.c2_m: m_data += f"競合B: {fmt_m(st.session_state.c2_m)}\n"

            sys_msg = (
                "あなたは丁寧で論理的な一流のWebストラテジストです。\n"
                "制作会社の社長が現場に改善指示を出せるよう、以下のルールを厳守してレポートを作成してください。\n\n"
                "【記述の絶対ルール】\n"
                "1. 口調：丁寧な『ですます調』を徹底してください。命令口調（〜せよ、〜すること）は厳禁です。\n"
                "2. 構造：各項目（EEAT、SEO等）を『事実：』と『示唆：』の2つの見出しに分けて記述してください。\n"
                "   - 『事実：』項目では、物理構造数値と競合の具体的な施策を客観的に記述します。\n"
                "   - 『示唆：』項目では、その事実が招くリスクと、取るべき戦略的な改善策を専門的な視点で提言します。\n"
                "3. 深度：EEAT（専門性・権威性・信頼性）やSEO（内部構造・サイト構造等）の各小分類を省略せず、すべて独立した項目として重厚に分析してください。\n"
                "4. 短文：文章は短く切り、改行を多用して可読性を高めてください。"
            )
            
            user_msg = (
                f"【対象業界】: {st.session_state.industry}\n"
                f"【物理構造データ】\n{m_data}\n"
                f"【自社テキスト抜粋】: {st.session_state.my_m['text'][:3500]}\n\n"
                "以下の構成でレポートを出力してください：\n\n"
                "### ■ 物理構造スペック比較\n"
                "自社と競合の数値を一覧表形式で対比させてください。\n\n"
                "### ■1. コンテンツの実務解像度分析\n"
                "#### 【実績の裏付け（証拠の密度）】\n"
                "数値出現数やページ数から分析してください。\n\n"
                "### ■2. 成約導線とスマホUXの物理解析\n"
                "#### 【CTAとマイクロコピー】\n"
                "#### 【テキスト構造と可読性】\n"
                "平均段落長の差（文字の壁）から診断してください。\n\n"
                "### ■3. EEAT 診断（情報の権威性と信頼性）\n"
                "#### 【専門性（Expertise）】\n"
                "#### 【権威性（Authoritativeness）】\n"
                "#### 【信頼性（Trustworthiness）】\n"
                "画像のAlt欠落数など、実装品質についても言及してください。\n\n"
                "### ■4. SEO / LLMO 診断（構造と鮮度）\n"
                "#### 【内部構造（見出し・リンク）】\n"
                "#### 【サイト構造（階層・網羅性）】\n"
                "#### 【情報の鮮度と生存確認】\n\n"
                "### ■5. 自社が勝つための戦略的コンテンツ案 5案\n"
                "### ■6. 最優先改善アクションプラン（自社用）"
            )
            
            diag_res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}], temperature=0.0)
            st.session_state.full_report = diag_res.choices[0].message.content
            st.session_state.step = 3

if st.session_state.step >= 3:
    st.divider()
    st.markdown("## 🛡️ 戦略・構造・数値 統合診断レポート")
    st.markdown(st.session_state.full_report)
    st.divider()
    st.subheader("📋 レポートを保存する")
    copy_to_clipboard_js(st.session_state.full_report)
