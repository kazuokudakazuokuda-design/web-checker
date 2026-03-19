import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from urllib.parse import urlparse, urljoin
import time

# --- 1. 基本設定 ---
st.set_page_config(page_title="🛡️ Web構造比較診断", layout="wide")

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
except:
    st.error("エラー：StreamlitのSecretsに 'GEMINI_API_KEY' が設定されていません。")
    st.stop()

# --- 2. 物理構造解析関数 ---
def analyze_site_physics(url, limit_pages=50):
    for i in range(2):
        try:
            url = url.strip()
            if not url.startswith("http"): url = "https://" + url
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 200:
                r.encoding = r.apparent_encoding
                soup = BeautifulSoup(r.text, "html.parser")
                break
            else:
                if i == 0: {time.sleep(2)}; continue
                return {"error": True, "message": f"Status: {r.status_code}", "desc": "アクセス拒否"}
        except Exception as e:
            if i == 0: {time.sleep(2)}; continue
            return {"error": True, "message": str(e), "desc": "接続エラー"}

    try:
        m_desc = soup.find("meta", attrs={"name": "description"})
        h1_count = len(soup.find_all('h1'))
        h2_count = len(soup.find_all('h2'))
        all_links = soup.find_all('a', href=True)
        domain = urlparse(url).netloc
        internal_links = [urljoin(url, l['href']) for l in all_links if domain in urljoin(url, l['href'])]
        
        has_sitemap = "あり" if any(x in r.text for x in ["sitemap", "xml"]) else "不明"

        asset_counts = {"事例": 0, "ブログ": 0, "料金": 0, "会社情報": 0, "問い合わせ": 0}
        for link in list(set(internal_links))[:limit_pages]:
            l_lower = link.lower()
            if any(x in l_lower for x in ["case", "jirei", "works", "portfolio", "results", "archives"]): asset_counts["事例"] += 1
            if any(x in l_lower for x in ["blog", "column", "news"]): asset_counts["ブログ"] += 1
            if any(x in l_lower for x in ["price", "fee", "hiyo"]): asset_counts["料金"] += 1
            if any(x in l_lower for x in ["about", "company", "office", "access"]): asset_counts["会社情報"] += 1
            if any(x in l_lower for x in ["contact", "inquiry", "entry"]): asset_counts["問い合わせ"] += 1

        return {
            "title": soup.title.string if soup.title else "No Title",
            "desc": m_desc["content"] if m_desc else "未設定",
            "h1": h1_count, "h2": h2_count, "total_links": len(all_links),
            "internal_links_count": len(internal_links),
            "sitemap": has_sitemap,
            "asset_counts": asset_counts,
            "body_text": soup.get_text()[:1500]
        }
    except Exception as e:
        return {"error": True, "message": str(e), "desc": "解析失敗"}

# --- 3. メインUI ---
st.title("🛡️ 経営戦略型・Web構造比較診断")

col_u1, col_u2, col_u3 = st.columns(3)
with col_u1: my_url = st.text_input("自社URL")
with col_u2: comp1_url = st.text_input("競合A")
with col_u3: comp2_url = st.text_input("競合B")

st.write("---")
if 'step' not in st.session_state: st.session_state.step = 1

# --- STEP 1：業界判定 ---
if st.button("STEP 1：業界を判定"):
    if not my_url or not comp1_url:
        st.warning("自社URLと競合AのURLを入力してください。")
    else:
        with st.spinner("解析中..."):
            st.session_state.my_data = analyze_site_physics(my_url)
            st.session_state.c1_data = analyze_site_physics(comp1_url)
            st.session_state.c2_data = analyze_site_physics(comp2_url) if comp2_url else None
            
            if "error" in st.session_state.my_data or "error" in st.session_state.c1_data:
                st.error("URL解析に失敗しました。対象サイトが拒否しているか、URLが不正です。")
            else:
                prompt_s1 = f"以下から業界名を単語1つで回答せよ。解説不要。\n自社Meta: {st.session_state.my_data.get('desc','')}\n競合Meta: {st.session_state.c1_data.get('desc','')}"
                st.session_state.industry = model.generate_content(prompt_s1).text.strip()
                st.session_state.step = 2

if st.session_state.step >= 2:
    st.write("### STEP 1：業界の特定")
    st.write("AI判定の業界名です。必要に応じて修正してください。")
    st.session_state.industry = st.text_input("業界名", st.session_state.industry)

    # --- STEP 2 & 3 & 4：戦略的診断ロジック ---
    if st.button("診断レポートを一括生成"):
        with st.spinner("営業戦略の観点から分析中..."):
            def get_stats(d):
                if not d or "error" in d: return "取得不可"
                return f"title:{d['title']}, h1:{d['h1']}, h2:{d['h2']}, a:{d['total_links']}, 内部リンク:{d['internal_links_count']}, 資産:{d['asset_counts']}"
            
            # AIへの共通指示（システム指示）
            common_instruction = f"""
            あなたは企業の営業戦略をWeb構造から読み解く参謀です。
            SEOの数値を前提としつつ、その先にある「商売の勝ち負け（受注・成約）」に踏み込んで分析してください。
            比喩（蛇口、器等）や過激な表現（毒、煽り等）は厳禁とし、実務的なビジネス用語のみを使用してください。
            
            評価の3軸：
            1. 信頼獲得の速度：実績や料金の提示が、どれだけ早く顧客を安心させ、他社への目移りを防いでいるか。
            2. 検討の独占率：サイト構造（見出し等）が、顧客の悩みに即座に回答し、他社比較を無効化できているか。
            3. 営業の効率化：導線設計が、検討度合いの低い客をフィルタリングし、成約に近い客を運んでいるか。
            """

            # STEP 2 プロンプト
            prompt_s2 = f"{common_instruction}\n[1]調査レポートと[2]分析コメント(### 分析コメント)を出力せよ。事例0件時は構造的要因の可能性に言及せよ。\n自社:{get_stats(st.session_state.my_data)}\n競合A:{get_stats(st.session_state.c1_data)}"
            res2 = model.generate_content(prompt_s2).text
            st.session_state.report_s2, st.session_state.comm_s2 = res2.split("### 分析コメント") if "### 分析コメント" in res2 else (res2, "")

            # STEP 3 プロンプト（因果関係の解明）
            prompt_s3 = f"{common_instruction}\n上記レポートに基づき「事実：」「示唆：」形式で、SEOの先にある商売上の因果関係を診断せよ。提言は含めない。\n原文: {st.session_state.report_s2}"
            st.session_state.report_s3 = model.generate_content(prompt_s3).text

            # STEP 4 プロンプト（戦略的集中）
            prompt_s4 = f"{common_instruction}\nこれまでの診断に基づき「どこで勝つか」を主眼に提言せよ。\n1.サマリー(所感と提言骨子)\n2.優先度別提言(最優先/優先/次の課題)\n3.新コンテンツ案(受注率を高める3案)\n診断: {st.session_state.report_s3}"
            st.session_state.report_s4 = model.generate_content(prompt_s4).text
            st.session_state.step = 4

    if 'report_s2' in st.session_state:
        st.write("---")
        st.subheader("STEP 2：調査レポート")
        st.markdown(st.session_state.report_s2)
        if st.session_state.comm_s2: st.info(st.session_state.comm_s2.strip())
        
        st.subheader("STEP 3：診断レポート（商売の因果関係）")
        st.markdown(st.session_state.report_s3)
        
        st.subheader("STEP 4：提言レポート（戦略的集中）")
        st.markdown(st.session_state.report_s4)
