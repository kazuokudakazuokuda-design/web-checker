import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import streamlit.components.v1 as components
import re

# 1. 画面構成
st.set_page_config(page_title="🛡️ 業界特化型Webサイト診断", layout="wide")
st.title("🛡️ 業界特化型Webサイト診断")
st.caption("※物理数値エビデンスに基づく、EEAT・SEO・UXの統合戦略診断レポート。")

# --- タイトル直下に入力エリア（スマホ配慮） ---
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
        
        # 不要タグ削除
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
            "text": text_content[:7000] # テキストもしっかり渡す
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
        with st.spinner("数値と戦略の統合レポートを構築中...（省略なし）"):
            
            def fmt_m(m):
                if not m: return "データなし"
                return (f"推定ページ数:{m['unique_links']}, 見出し数:{m['h_count']}, リンク総数:{m['a_count']}, "
                        f"画像数:{m['img_count']}(Alt欠落:{m['alt_missing']}), 平均段落長:{m['avg_p_len']}字, "
                        f"数値/固有名詞出現数:{m['num_count']}, FAQ:{m['has_faq']}, サービス案内:{m['has_service']}")

            m_data = f"【物理数値エビデンス】\n自社: {fmt_m(st.session_state.my_m)}\n競合A: {fmt_m(st.session_state.c1_m)}\n"
            if st.session_state.c2_m: m_data += f"競合B: {fmt_m(st.session_state.c2_m)}\n"

            sys_msg = (
                "あなたは一切の妥協を許さない、冷徹かつ礼節ある一流のWebストラテジストです。\n"
                "制作会社の社長が、現場を叱咤激励し、具体的な改善を即座に命令できるレベルの『戦略指示書』を作成してください。\n"
                "【重要：記述ルール】\n"
                "1. 数値エビデンスを提示するだけで満足せず、必ずそこから『戦略的欠落』を抉り出すこと。\n"
                "2. 以前合格したEEAT・SEOの各分類を1つも省略せず、すべて独立した小見出しで重厚に記述すること。\n"
                "3. 短文で切り、改行を多用する。抽象的なポエムを禁止し、実務上の『事実』と『過酷な提言』を分けること。\n"
                "4. 制作会社として、Alt欠落などの初歩的ミスは技術的信頼の欠如として厳しく断定すること。"
            )
            
            user_msg = (
                f"【対象業界】: {st.session_state.industry}\n"
                f"【物理構造データ】\n{m_data}\n"
                f"【自社テキスト抜粋】: {st.session_state.my_m['text'][:3000]}\n\n"
                "以下の構成を厳守し、各小見出しにおいて圧倒的な解像度で記述してください：\n\n"
                "### ■ 物理構造スペック比較（事実）\n"
                "自社・競合の数値を一覧化し、物量の格差を視覚化せよ。\n\n"
                "### ■1. コンテンツの実務解像度分析\n"
                "#### 【実績の裏付け（証拠の密度）】\n"
                "数値出現数やページ数から、実績を『単なる宣伝文句』から『信頼の証拠』へ昇華させるための提言を詳述せよ。\n\n"
                "### ■2. 成約導線とスマホUXの物理解析\n"
                "#### 【CTAとマイクロコピー】\n"
                "ボタン周辺の心理障壁の除去について診断。\n"
                "#### 【テキスト構造と可読性】\n"
                "平均段落長の差（文字の壁）から、スマホユーザーの離脱リスクを数値で証明せよ。\n\n"
                "### ■3. EEAT 診断（情報の権威性と信頼性）\n"
                "#### 【専門性（Expertise）】\n"
                "見出し数やトピックの細分化度から、技術解説の解像度不足を抉り出せ。\n"
                "#### 【権威性（Authoritativeness）】\n"
                "外部評価、創業年数、メディア実績の活用度を比較診断せよ。\n"
                "#### 【信頼性（Trustworthiness）】\n"
                "制作会社としての実装品質（Alt欠落等）から透明性と誠実さを問え。\n\n"
                "### ■4. SEO / LLMO 診断（構造と鮮度）\n"
                "#### 【内部構造（見出し・リンク）】\n"
                "見出しの論理性とアンカーテキストの不備を診断せよ。\n"
                "#### 【サイト構造（階層・網羅性）】\n"
                "内部リンク数から、トピッククラスターの構築不全を指摘せよ。\n"
                "#### 【情報の鮮度と生存確認】\n"
                "更新頻度が対外的な信頼に与えるダメージを論じよ。\n\n"
                "### ■5. 自社が勝つための戦略的コンテンツ案 5案\n"
                "数値差を埋めるための具体的な企画を提示せよ。\n"
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
    st.subheader("📋 レポートをコピーする")
    copy_to_clipboard_js(st.session_state.full_report)
