import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, unquote
import google.generativeai as genai
import time
import re

# =============================================
# 基本設定
# =============================================
st.set_page_config(page_title="Web構造比較診断", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans JP', sans-serif;
}
h1 { font-size: 1.8em !important; font-weight: 700 !important; }
h2 { font-size: 1.4em !important; font-weight: 700 !important; margin-top: 1.5em !important; border-left: 4px solid #2563eb; padding-left: 12px; }
h3 { font-size: 1.15em !important; font-weight: 700 !important; margin-top: 1.2em !important; }
table { width: 100% !important; border-collapse: collapse !important; }
td, th { padding: 10px 14px !important; border: 1px solid #e2e8f0 !important; font-size: 0.95em !important; word-break: break-word; }
th { background-color: #f1f5f9 !important; font-weight: 700 !important; }
.stButton > button {
    background-color: #2563eb;
    color: white;
    font-weight: 700;
    border-radius: 6px;
    padding: 0.5em 2em;
    border: none;
}
.stButton > button:hover { background-color: #1d4ed8; }
.disclaimer {
    background: #fef9c3;
    border-left: 4px solid #eab308;
    padding: 10px 16px;
    border-radius: 4px;
    font-size: 0.88em;
    color: #713f12;
    margin-bottom: 1.5em;
}
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Web構造比較診断")
st.markdown("""
<div class="disclaimer">
本診断は生成AIによる一次診断です。推測・不正確な情報を含む場合があります。
</div>
""", unsafe_allow_html=True)

st.markdown("""
自社と競合サイトのURLを入力するだけで、サイト構造・コンテンツ・SEO・EEAT・問い合わせ導線の6軸を自動診断します。  
比較表・軸別スコア・優先度付きの改善提案・推奨コンテンツ案をまとめて出力します。
""")

# =============================================
# Gemini 初期化
# =============================================
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel("models/gemini-2.5-flash")
except Exception as e:
    st.error(f"APIキー設定エラー: {e}")
    st.stop()

# =============================================
# 定数
# =============================================
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

PAGE_TYPE_KEYWORDS = {
    "service":  ["service", "services", "solution", "product", "jigyou", "jigyo"],
    "case":     ["case", "cases", "jirei", "works", "result", "portfolio", "jisseki"],
    "blog":     ["blog", "column", "news", "article", "media", "insight"],
    "recruit":  ["recruit", "career", "job", "saiyou", "saiyo"],
    "about":    ["about", "company", "gaisha", "kaisha", "profile", "vision", "mission"],
}

EVAL_AXES = [
    ("structure",  "サイト構造の明快さ"),
    ("content",    "コンテンツの網羅性"),
    ("case_study", "事例・実績の充実度"),
    ("eeat",       "EEAT（経験・専門性・権威性・信頼性）"),
    ("seo_llmo",   "SEO／LLMO対応"),
    ("cta",        "問い合わせ導線の設計"),
]

# =============================================
# クロールレイヤー
# =============================================
def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    return url

def fetch_page(url: str, timeout: int = 12):
    """1ページ取得。失敗時はNoneを返す。"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return BeautifulSoup(r.text, "html.parser")
    except Exception:
        return None

def extract_main_text(soup: BeautifulSoup, max_chars: int = 2000) -> str:
    """ナビ・フッター・スクリプトを除いたメインテキストを抽出。"""
    for tag in soup(["nav", "footer", "header", "script", "style", "noscript"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.find("body")
    if not main:
        return ""
    text = re.sub(r'\s+', ' ', main.get_text(separator=" ")).strip()
    return text[:max_chars]

def classify_page_type(url: str) -> str:
    """URLパスからページ種別を推定。日本語URLにも対応。"""
    path = unquote(urlparse(url).path.lower())
    for ptype, keywords in PAGE_TYPE_KEYWORDS.items():
        if any(kw in path for kw in keywords):
            return ptype
    return "other"

def crawl_site(top_url: str, max_pages: int = 7):
    """
    トップページ＋種別ごとに代表1ページを取得（合計最大max_pages）。
    戻り値: {"top": {...}, "service": {...}, "case": {...}, ...}
    """
    top_url = normalize_url(top_url)
    result = {}

    # トップページ取得
    soup = fetch_page(top_url)
    if soup is None:
        return {"error": True, "message": f"{top_url} を取得できませんでした。"}

    result["top"] = {
        "url": top_url,
        "title": soup.title.string.strip() if soup.title else "No Title",
        "meta_desc": (soup.find("meta", attrs={"name": "description"}) or {}).get("content", "未設定"),
        "h1": len(soup.find_all("h1")),
        "h2": len(soup.find_all("h2")),
        "text": extract_main_text(soup),
    }

    # 内部リンク収集
    domain = urlparse(top_url).netloc
    all_links = soup.find_all("a", href=True)
    internal_urls = list({
        urljoin(top_url, a["href"])
        for a in all_links
        if domain in urljoin(top_url, a["href"])
        and not urljoin(top_url, a["href"]).endswith((".pdf", ".jpg", ".png", ".zip"))
    })

    result["top"]["internal_link_count"] = len(internal_urls)

    # ページ種別ごとに代表1ページを取得
    found_types = set()
    pages_fetched = 1

    for url in internal_urls:
        if pages_fetched >= max_pages:
            break
        ptype = classify_page_type(url)
        if ptype == "other" or ptype in found_types:
            continue

        page_soup = fetch_page(url)
        if page_soup is None:
            continue

        result[ptype] = {
            "url": url,
            "h1": len(page_soup.find_all("h1")),
            "h2": len(page_soup.find_all("h2")),
            "text": extract_main_text(page_soup),
        }
        found_types.add(ptype)
        pages_fetched += 1
        time.sleep(0.5)  # 過負荷防止

    # ページ種別ごとのカウント（リンクベース）
    type_counts = {k: 0 for k in PAGE_TYPE_KEYWORDS}
    for url in internal_urls:
        pt = classify_page_type(url)
        if pt in type_counts:
            type_counts[pt] += 1
    result["type_counts"] = type_counts

    return result

# =============================================
# 評価レイヤー
# =============================================
def build_site_summary(label: str, data: dict) -> str:
    """サイトデータを文字列サマリーに変換してプロンプトに渡す。"""
    lines = [f"【{label}】"]
    top = data.get("top", {})
    lines.append(f"タイトル: {top.get('title', '')}")
    lines.append(f"メタディスクリプション: {top.get('meta_desc', '')}")
    lines.append(f"H1数: {top.get('h1', 0)} / H2数: {top.get('h2', 0)}")
    lines.append(f"内部リンク数: {top.get('internal_link_count', 0)}")
    tc = data.get("type_counts", {})
    lines.append(
        f"ページ種別リンク数 - "
        f"サービス:{tc.get('service', 0)} "
        f"事例:{tc.get('case', 0)} "
        f"ブログ:{tc.get('blog', 0)} "
        f"採用:{tc.get('recruit', 0)} "
        f"会社概要:{tc.get('about', 0)}"
    )
    lines.append(f"トップページ本文抜粋: {top.get('text', '')[:800]}")
    for ptype in ["service", "case", "blog", "about"]:
        if ptype in data:
            lines.append(f"{ptype}ページ本文抜粋: {data[ptype].get('text', '')[:500]}")
    return "\n".join(lines)

def run_diagnosis(industry: str, my_data: dict, c1_data: dict, c2_data) -> str:
    """Geminiに診断を依頼し、レポートテキストを返す。"""
    my_summary = build_site_summary("自社", my_data)
    c1_summary = build_site_summary("競合A", c1_data)
    c2_summary = build_site_summary("競合B", c2_data) if c2_data else "競合B: データなし"
    axes_str = "\n".join([f"- {label}" for _, label in EVAL_AXES])

    # メタディスクリプション抽出
    my_desc  = my_data.get("top", {}).get("meta_desc", "未設定")
    c1_desc  = c1_data.get("top", {}).get("meta_desc", "未設定")
    c2_desc  = c2_data.get("top", {}).get("meta_desc", "未設定") if c2_data else "データなし"

    prompt = f"""
あなたはWebサイト診断の専門家です。以下のデータをもとに、営業提案の下準備として使える診断レポートを作成してください。
挨拶・前置き・後書きは一切不要です。レポート本文のみ出力してください。

【業種】{industry}

{my_summary}

{c1_summary}

{c2_summary}

---

## 出力形式（必ずこの順序・構成で出力すること）

### サマリー

【診断結果】
「御社のサイトを拝見したところ、〜」という書き出しで始め、サイト全体の現状を5〜6文で説明してください。
競合との比較を交えながら、強みと課題を具体的に記述してください。
数値（H2数、内部リンク数、事例数など）を自然に組み込んでください。

【提案】
（ここで必ず1行空けること）
上記の診断結果を踏まえ、営業担当者が顧客に提案する際の骨子を5〜6文で記述してください。
「〜を強化することで、〜が期待できます」という形式で、具体的な改善方向と期待効果をセットで伝えてください。

---

### 各社メタディスクリプション
以下を原文のまま、一字一句変えずに表示してください。要約・改変は禁止です。

- 自社：{my_desc}
- 競合A：{c1_desc}
- 競合B：{c2_desc}

---

### 比較表
Markdown表で出力してください。
行：自社 / 競合A / 競合B（データなしの場合は「-」）
列：H1数 / H2数 / 内部リンク数 / サービスページ数 / 事例ページ数 / ブログページ数

表の直後に必ず「※数値はリンク構造から推計した概算値です」と記載してください。

---

### 軸別診断
以下の6軸それぞれについて診断してください。
{axes_str}

各軸の記述形式（見出しは日本語名のみ。「structure:」などの英語キーは絶対に含めないこと）：
#### [日本語の軸名のみ]（自社スコア: X/10）

**診断結果**
数値を根拠にした現状説明。{industry}業界の標準と比較して評価してください。

**リスク・要チェック**
放置した場合の具体的なリスク。

**改善インパクト**
改善した場合にユーザー行動・問い合わせ数にどう影響するか。

---

### 提案（優先度順）

#### 最優先

**タイトル**：
（ここで1行空けること）
**施策内容**：具体的な施策を記述。
（ここで1行空けること）
**期待効果**：期待される効果を記述。

#### 優先

**タイトル**：
（ここで1行空けること）
**施策内容**：具体的な施策を記述。
（ここで1行空けること）
**期待効果**：期待される効果を記述。

#### 次の課題

**タイトル**：
（ここで1行空けること）
**施策内容**：具体的な施策を記述。
（ここで1行空けること）
**期待効果**：期待される効果を記述。

---

### 推奨コンテンツ3案
{industry}業界のユーザーが問い合わせ前に調べる情報を起点に、以下の形式で3案提示してください。

**案1**
- タイトル：
- ターゲット：
- 構成（3〜5項目）：
- 制作上のポイント：

**案2**（同形式）

**案3**（同形式）

---

重要ルール：
- メタディスクリプションは原文のまま表示し、要約・改変・省略は絶対禁止
- 軸別診断の見出しに英語キー（structure: 等）を含めないこと
- 「○○業界では〜」など業種に即した具体的な表現を使う
- スコアは根拠のある採点をすること。全項目を高くしない
- 不確かな日付・未来日付の指摘は禁止
"""

    response = model.generate_content(prompt)
    return response.text

# =============================================
# UI
# =============================================
st.subheader("診断対象URL・業種を入力")

col1, col2, col3 = st.columns(3)
with col1:
    my_url = st.text_input("自社URL", placeholder="https://example.com")
with col2:
    c1_url = st.text_input("競合A URL", placeholder="https://comp-a.com")
with col3:
    c2_url = st.text_input("競合B URL（任意）", placeholder="https://comp-b.com")

st.caption("業種が具体的なほど、業種に即した診断結果になります。「製造業」より「電子部品製造業」、「医師」より「皮膚科クリニック」のように入力してください。")
industry = st.text_input(
    "業種（必須）",
    placeholder="例：電子部品製造業 / 皮膚科クリニック / 注文住宅工務店 / BtoB SaaS",
)

run_btn = st.button("診断を実行する", disabled=not (my_url and c1_url and industry))

if run_btn:
    # ステートリセット
    for key in ["my_data", "c1_data", "c2_data", "report"]:
        st.session_state.pop(key, None)

    with st.spinner("サイトをクロール中..."):
        my_data = crawl_site(my_url)
        c1_data = crawl_site(c1_url)
        c2_data = crawl_site(c2_url) if c2_url.strip() else None

    # エラーチェック
    errors = []
    for data, label in [(my_data, "自社"), (c1_data, "競合A"), (c2_data, "競合B")]:
        if data and "error" in data:
            errors.append(f"**{label}**：{data['message']}")

    if errors:
        for e in errors:
            st.error(e)
        st.info("WAF等によりブロックされている可能性があります。URLを確認するか、別のサイトでお試しください。")
    else:
        st.session_state.my_data = my_data
        st.session_state.c1_data = c1_data
        st.session_state.c2_data = c2_data

        with st.spinner("AIが診断レポートを生成中...（30〜60秒かかる場合があります）"):
            report = run_diagnosis(industry, my_data, c1_data, c2_data)
            st.session_state.report = report

# レポート表示
if "report" in st.session_state:
    st.divider()
    st.markdown(st.session_state.report)

    st.divider()
    col_copy, col_reset = st.columns([3, 1])
    with col_copy:
        st.text_area(
            "レポートをコピーする",
            value=st.session_state.report,
            height=200,
            help="このテキストエリアから全文コピーできます"
        )
    with col_reset:
        if st.button("🔄 新しい診断を始める"):
            for key in ["my_data", "c1_data", "c2_data", "report"]:
                st.session_state.pop(key, None)
            st.rerun()
