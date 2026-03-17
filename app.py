import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import streamlit.components.v1 as components
import re

# 1. 画面構成
st.set_page_config(page_title="🛡️ 業界特化型Webサイト診断", layout="wide")
st.title("🛡️ 業界特化型Webサイト診断")
st.caption("※物理構造（数値）とテキスト解析による一次診断です。実務の指標としてご活用ください。")

# --- タイトル直下に入力エリアを配置 ---
st.divider()
st.subheader("🔍 診断対象の設定")
col1, col2, col3 = st.columns(3)

with col1:
    my_url = st.text_input("自社URL", placeholder="https://example.com")
with col2:
    comp1_url = st.text_input("競合A", placeholder="https://competitor-a.com")
with col3:
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
        # 簡易的な内部リンク（ドメイン含む、または相対パス）の抽出
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
        
        # 数字・固有名詞（大文字開始やカタカナ）の出現数（簡易カウント）
        nums = len(re.findall(r'\d+', text_content))
        
        # 特定要素の検出
        has_faq = any(k in text_content for k in ["よくある質問", "FAQ", "Q&A", "疑問"])
        has_service = any(k in text_content for k in ["サービス", "業務一覧", "メニュー", "料金"])

        metrics = {
            "unique_links": unique_internal_links, # ページ数（推定）
            "h_count": len(h_tags),
            "a_count": len(links),
            "img_count": len(img_tags),
            "alt_missing": alt_missing,
            "avg_p_len": int(avg_p_len),
            "num_count": nums,
            "has_faq": "あり" if has_faq else "なし",
            "has_service": "あり" if has_service else "なし",
            "text": text_content[:6000] # プロンプト用テキスト
        }
        
        meta_desc = soup.find("meta", attrs={"name": "description"})
        metrics["description"] = meta_desc["content"].strip() if meta_desc else "未設定"
        
        return metrics
    except Exception as e:
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

# ステップ管理
if st.button("STEP 1: 物理構造を計測"):
    if not my_url or not comp1_url:
        st.error("自社と競合AのURLは必須です。")
    else:
        with st.spinner("数値を計測中..."):
            st.session_state.my_m = get_site_metrics(my_url)
            st.session_state.c1_m = get_site_metrics(comp1_url)
            st.session_state.c2_m = get_site_metrics(comp2_url) if comp2_url else None
            st.session_state.urls = {"my": my_url, "c1": comp1_url, "c2": comp2_url if comp2_url else "-"}
            
            ind_prompt = f"業界名を回答せよ。余計な言葉は不要。\n\nテキスト:{st.session_state.my_m['text']}"
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": ind_prompt}],
                temperature=0.0
            )
            st.session_state.industry = response.choices[0].message.content.replace("業界", "")
            st.session_state.step = 2

if st.session_state.step >= 2:
    st.divider()
    st.subheader("📌 戦略診断の実行")
    industry_input = st.text_input("特定された業界", value=st.session_state.industry)
    
    if st.button("STEP 2: 数値比較レポートを生成"):
        st.session_state.industry = industry_input
        with st.spinner("物理数値の差分から戦略を構築中..."):
            
            # AIに渡す数値データの整理
            def fmt_m(m):
                if not m: return "データなし"
                return (f"推定ページ数:{m['unique_links']}, 見出し数:{m['h_count']}, "
                        f"リンク総数:{m['a_count']}, 画像数:{m['img_count']}(Alt未設定:{m['alt_missing']}), "
                        f"平均段落長:{m['avg_p_len']}字, 数値出現数:{m['num_count']}, "
                        f"FAQ:{m['has_faq']}, サービス一覧:{m['has_service']}")

            m_data = f"【自社】\n{fmt_m(st.session_state.my_m)}\n\n"
            m_data += f"【競合A】\n{fmt_m(st.session_state.c1_m)}\n\n"
            if st.session_state.c2_m:
                m_data += f"【競合B】\n{fmt_m(st.session_state.c2_m)}\n"

            sys_msg = (
                "あなたは冷徹かつ礼節あるWebコンサルタントです。\n"
                "提示された『物理構造数値』を最優先の事実として扱い、以下の順序で回答してください。\n"
                "1. 数値の提示: 項目ごとに自社と競合の数値を並べる。\n"
                "2. 差分分析: 数値の差がどのような戦略的劣後・優位を生んでいるか断定する。\n"
                "3. 実務提言: 社長が現場に即指示できるレベルで具体的対策を書く。\n\n"
                "文章ルール:\n"
                "- 短文で切る。改行を多用する。\n"
                "- 抽象的な『がんばりましょう』は禁止。数値に基づく『構造改革』を論じる。\n"
                "- 画像のAlt未設定などは制作会社として技術的な不備として厳しく指摘する。"
            )
            
            user_msg = (
                f"【対象業界】: {st.session_state.industry}\n"
                f"【物理構造データ】\n{m_data}\n"
                f"【自社テキスト抜粋】: {st.session_state.my_m['text'][:2000]}\n\n"
                "上記データに基づき、以下の構成でレポートを作成してください。\n\n"
                "### ■1. コンテンツ戦力分析（ページ数・網羅性）\n"
                "推定ページ数と内部リンク数の差から、サイトの『厚み』を診断。\n"
                "### ■2. 論理構造と可読性（見出し・段落）\n"
                "見出し数と段落長の差から、スマホ時代の読了率を診断。\n"
                "### ■3. 技術的誠実さとSEO（画像・Alt）\n"
                "画像数とAlt未設定数から、実装の丁寧さを診断。\n"
                "### ■4. 営業導線の設計（FAQ・サービス）\n"
                "FAQやサービス一覧の有無から、成約への親切心を診断。\n"
                "### ■5. 具体性と説得力（数値出現率）\n"
                "テキスト内の数字出現頻度から、実績の証拠密度を診断。\n"
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
    st.markdown("## 🛡️ 物理構造比較・戦略診断レポート")
    st.markdown(st.session_state.full_report)
    st.divider()
    st.subheader("📋 レポートを保存する")
    copy_to_clipboard_js(st.session_state.full_report)
