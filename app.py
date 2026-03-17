import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import streamlit.components.v1 as components
import re

# 1. 画面構成
st.set_page_config(page_title="🛡️ 戦略的Webサイト比較診断ツール", layout="wide")
st.title("🛡️ 戦略的Webサイト比較診断ツール")
st.caption("※物理数値と業界文脈を解析し、事実と示唆に基づいた改善指針を提示します。")

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
        
        # 解析用にスクリプト等を除去
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
        has_service = any(k in text_content for k in ["サービス", "案内", "メニュー", "料金"])

        # 日付検索
        dates = re.findall(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}', text_content)
        latest_date = max(dates) if dates else "不明"

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
            "latest_date": latest_date,
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

# --- STEP 1 ---
if st.button("STEP 1: サイト情報を解析"):
    if not my_url or not comp1_url:
        st.error("自社と競合AのURLは必須です。")
    else:
        with st.spinner("診断中"):
            st.session_state.my_m = get_site_metrics(my_url)
            st.session_state.c1_m = get_site_metrics(comp1_url)
            st.session_state.c2_m = get_site_metrics(comp2_url) if comp2_url else None
            
            if not st.session_state.my_m or not st.session_state.c1_m:
                st.error("サイトの解析に失敗しました。URLを確認してください。")
            else:
                ind_prompt = f"このWebサイトの業界名を回答してください。余計な言葉は不要です。\n\nテキスト:{st.session_state.my_m['text'][:2000]}"
                response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": ind_prompt}], temperature=0.0)
                st.session_state.industry = response.choices[0].message.content.replace("業界", "")
                st.session_state.step = 2

# --- STEP 2 ---
if st.session_state.step >= 2:
    st.divider()
    st.subheader("📌 戦略診断の実行")
    industry_input = st.text_input("特定された業界", value=st.session_state.industry)
    
    if st.button("STEP 2: 詳細診断レポートを生成"):
        st.session_state.industry = industry_input
        with st.spinner("診断中"):
            
            def fmt_m(m):
                if not m: return "データなし"
                return (f"推定ページ数:{m['unique_links']}, 見出し数:{m['h_count']}, リンク総数:{m['a_count']}, "
                        f"画像数:{m['img_count']}(Alt欠落:{m['alt_missing']}), 平均段落長:{m['avg_p_len']}字, "
                        f"数値/固有名詞出現数:{m['num_count']}, FAQ:{m['has_faq']}, サービス案内:{m['has_service']}, 最新更新日:{m['latest_date']}")

            m_data = f"【物理数値エビデンス】\n自社: {fmt_m(st.session_state.my_m)}\n競合A: {fmt_m(st.session_state.c1_m)}\n"
            if st.session_state.c2_m: m_data += f"競合B: {fmt_m(st.session_state.c2_m)}\n"

            sys_msg = (
                f"あなたは{st.session_state.industry}業界に精通した、論理的で丁寧なWebストラテジストです。\n"
                "以下の【記述ルール】を厳守して診断レポートを作成してください。\n\n"
                "【記述ルール】\n"
                "1. 口調：常に丁寧な『ですます調』を使用してください。命令口調は厳禁です。\n"
                "2. 構造（1項〜4項）：各小見出しにおいて必ず『事実：』と『示唆：』の2つの見出しに分けて記述してください。\n"
                "   - 『事実：』では、数値データに加え、抽出テキストから『どのような専門用語があるか』『何が具体的に欠けているか』を客観的に特定してください。\n"
                "   - 『示唆：』では、その業界特性を踏まえ、『どのカテゴリをどのように肉付けすべきか』『どのようなリライトが有効か』、推測を含む具体的な方針を提示してください。\n"
                "3. 構造（5項〜6項）：事実・示唆の形式は不要です。具体的な企画案と実行手順を丁寧に記述してください。\n"
                "4. 精度：『〜を増やしましょう』といった抽象的な表現は避け、『〇〇という実績を、△△という切り口で分解した見出しを作成してください』といった具体的な指示レベルまで解像度を高めてください。"
            )
            
            user_msg = (
                f"【対象業界】: {st.session_state.industry}\n"
                f"【物理データ】\n{m_data}\n"
                f"【自社テキスト抜粋】: {st.session_state.my_m['text'][:4000]}\n\n"
                "以下の構成で出力してください：\n\n"
                "### ■ 物理構造スペック比較\n"
                "自社と競合の数値を整理して対比させてください。\n\n"
                "### ■1. コンテンツの実務解像度分析\n"
                "#### 【実績の裏付け（証拠の密度）】\n\n"
                "### ■2. 成約導線とスマホUXの物理解析\n"
                "#### 【CTAとマイクロコピー】\n"
                "#### 【テキスト構造と可読性】\n\n"
                "### ■3. EEAT 診断（情報の権威性と信頼性）\n"
                "#### 【専門性（Expertise）】\n"
                "#### 【権威性（Authoritativeness）】\n"
                "#### 【信頼性（Trustworthiness）】\n\n"
                "### ■4. SEO / LLMO 診断（構造と鮮度）\n"
                "#### 【内部構造（見出し・リンク）】\n"
                "#### 【サイト構造（階層・網羅性）】\n"
                "#### 【情報の鮮度と生存確認】\n\n"
                "### ■5. 自社が勝つための戦略的コンテンツ案 5案\n"
                "（業界特性を考慮した具体的なタイトルと内容を提示してください）\n\n"
                "### ■6. 最優先改善アクションプラン（自社用）\n"
                "（今日から着手すべき具体的な手順を提示してください）"
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
