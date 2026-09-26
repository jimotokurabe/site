"""じもとくらべ のページを data/*.json から作る。

  python3 tools/build.py                  # リポジトリ直下に公開用のページを作り直す
  python3 tools/build.py --out /tmp/x --draft --artifact /tmp/y
                                          # 下書き（検索に出さない・下書きの帯を出す）と、確認用ページの形
"""
import argparse
import json
import re
import shutil
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://jimotokurabe.jp/"

KINDS = {
    "give": ("もらえる", "返納した人に、券・カード・補助金などを出す"),
    "discount": ("安くなる", "運転経歴証明書を見せると、市町のバスなどの運賃が安くなる"),
    "elder": ("高齢者向け", "返納した人も使える、高齢者向けの移動の支援（75歳以上の人なども対象）"),
    "purchase": ("購入の補助", "シニアカーなどを買うときの費用を補助する"),
    "end": ("終了", "以前はあったが、受付を終えた"),
    "none": ("なし", "市町のページに「特典はない」と書かれている"),
    "notfound": ("記載なし", "市町のページに、独自の特典が書かれていない。「ない」とも書かれていないため、窓口で確かめる必要がある"),
}
FILTERS = [
    ("all", "すべて", None),
    ("give", "もらえる", {"give"}),
    ("discount", "安くなる", {"discount"}),
    ("elder", "高齢者向け", {"elder"}),
    ("purchase", "購入の補助", {"purchase"}),
    ("notfound", "記載なし", {"notfound"}),
    ("endnone", "終了・なし", {"end", "none"}),
]
HAS_BENEFIT = {"give", "discount", "elder", "purchase"}
FONTS = ("https://fonts.googleapis.com/css2?family=BIZ+UDPGothic:wght@400;700"
         "&family=Zen+Maru+Gothic:wght@700&display=swap")
SIZE_BOOT = ('<script>try{if(localStorage.getItem("jk-size")==="large")'
             'document.documentElement.setAttribute("data-size","large")}catch(e){}</script>')
SIZE_SCRIPT = """<script>
(function () {
  var root = document.documentElement;
  var buttons = document.querySelectorAll("[data-size-btn]");
  function set(size, save) {
    if (size === "large") root.setAttribute("data-size", "large");
    else root.removeAttribute("data-size");
    buttons.forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-size-btn") === size));
    });
    if (save) { try { localStorage.setItem("jk-size", size); } catch (e) {} }
  }
  set(root.getAttribute("data-size") === "large" ? "large" : "normal", false);
  buttons.forEach(function (b) {
    b.addEventListener("click", function () { set(b.getAttribute("data-size-btn"), true); });
  });
})();
</script>"""


def e(s):
    return escape(str(s), quote=True)


def jdate(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{y}年{m}月{d}日"


def shell(*, title, description, path, main, draft, draft_note="", scripts=""):
    canonical = SITE + path
    robots = '<meta name="robots" content="noindex">\n' if draft else ""
    banner = ""
    if draft:
        banner = ('<p class="draft">これは公開前の下書きです。' + draft_note + '</p>')
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
{robots}<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="じもとくらべ">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:locale" content="ja_JP">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="site.css">
{SIZE_BOOT}
</head>
<body>
<a class="skip" href="#main">本文へ移動</a>
<div class="wrap">
<header class="topbar">
  <a class="brand" href="./">じもと<span>くらべ</span></a>
  <div class="sizer" role="group" aria-label="文字の大きさ">
    <span>文字の大きさ</span>
    <button type="button" data-size-btn="normal" aria-pressed="true">標準</button>
    <button type="button" data-size-btn="large" aria-pressed="false">大きく</button>
  </div>
</header>
{banner}
<main id="main">
{main}
</main>
<footer class="footer">
  <nav aria-label="サイトの案内">
    <a href="./">トップ</a>
    <a href="about.html">運営者情報</a>
    <a href="privacy.html">プライバシーポリシー</a>
  </nav>
  <p>© 2026 じもとくらべ</p>
</footer>
</div>
{SIZE_SCRIPT}
{scripts}
</body>
</html>
"""


# ---------------- 一覧ページ ----------------

def fact(label, value):
    if not value:
        return ""
    na = value == "記載なし"
    shown = "ページに記載なし" if na else value
    cls = ' class="na"' if na else ""
    return f'    <div><dt>{e(label)}</dt><dd{cls}>{e(shown)}</dd></div>\n'


def card(c, checked):
    kind_label = KINDS[c["k"]][0]
    unit = "町" if c["n"].endswith("町") else "市"
    benefit = c["k"] in HAS_BENEFIT
    facts = ""
    if benefit:
        facts += fact("金額の目安", c.get("amt"))
        facts += fact("対象の年齢", c.get("age"))
        dl = c.get("dl")
        if dl != "申し込みはいりません":
            facts += fact("申し込み期限", dl)
    if c.get("apply"):
        facts += fact(c.get("apply_label", "申し込み先"), c["apply"])
    parts = [f'<p class="what">{e(c["what"])}</p>']
    if facts:
        parts.append(f'<dl class="facts">\n{facts}  </dl>')
    if c.get("note"):
        parts.append(f'<p class="note">{e(c["note"])}</p>')
    if c["k"] == "notfound":
        parts.append(f'<p class="note">くわしくは{unit}の窓口で確かめてください。'
                     '<a href="#statewide">県内どこでも使える割引</a>もあります。</p>')
    if c.get("flag"):
        parts.append(f'<p class="flag">確かめ方：{e(c["flag"])}</p>')
    if c.get("url"):
        src = c.get("src") or f"{unit}の公式ページ"
        link = (f'<a class="btn-src" href="{e(c["url"])}" target="_blank" rel="noopener">'
                f'{e(src)}を見る<span aria-hidden="true">↗</span></a>')
        dates = f'ページの日付：{e(c["upd"])}<br>確かめた日：{jdate(checked)}'
    else:
        link = f'<span class="empty-src">{unit}の公式ページ：見つかりませんでした</span>'
        dates = f'確かめた日：{jdate(checked)}'
    parts.append(f'<div class="card-foot">\n    {link}\n    <p class="dates">{dates}</p>\n  </div>')
    body = "\n  ".join(parts)
    notfound = " is-notfound" if c["k"] == "notfound" else ""
    return f"""<article class="card{notfound}" id="{c['slug']}" data-k="{c['k']}" aria-labelledby="{c['slug']}-h">
  <div class="card-head">
    <h3 class="city" id="{c['slug']}-h">{e(c['n'])}<span class="yomi">{e(c['y'])}</span></h3>
    <span class="chip k-{c['k']}">{e(kind_label)}</span>
  </div>
  {body}
</article>"""


LIST_SCRIPT = """<script>
(function () {
  function norm(s) {
    return String(s).normalize("NFKC")
      .replace(/[\\u30a1-\\u30f6]/g, function (c) { return String.fromCharCode(c.charCodeAt(0) - 0x60); })
      .replace(/\\s+/g, "").toLowerCase();
  }
  var q = document.getElementById("q");
  var groups = document.querySelectorAll(".pick-region");
  var none = document.getElementById("pick-none");
  q.addEventListener("input", function () {
    var v = norm(q.value), total = 0;
    groups.forEach(function (g) {
      var n = 0;
      g.querySelectorAll("a").forEach(function (a) {
        var hit = !v || norm(a.getAttribute("data-name")).indexOf(v) >= 0 || norm(a.getAttribute("data-yomi")).indexOf(v) >= 0;
        a.hidden = !hit;
        if (hit) n++;
      });
      g.hidden = n === 0;
      total += n;
    });
    none.hidden = total > 0;
  });

  var chips = document.querySelectorAll("#filters button");
  var cards = document.querySelectorAll(".card");
  var regions = document.querySelectorAll(".region");
  var count = document.getElementById("count");
  var SETS = { endnone: ["end", "none"] };
  function apply(f) {
    var shown = 0;
    chips.forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-f") === f)); });
    cards.forEach(function (c) {
      var k = c.getAttribute("data-k");
      var hit = f === "all" || (SETS[f] ? SETS[f].indexOf(k) >= 0 : k === f);
      c.hidden = !hit;
      if (hit) shown++;
    });
    regions.forEach(function (r) { r.hidden = !r.querySelector(".card:not([hidden])"); });
    count.textContent = f === "all" ? "41市町すべてを表示しています。" : "41市町のうち " + shown + "市町を表示しています。";
  }
  chips.forEach(function (b) { b.addEventListener("click", function () { apply(b.getAttribute("data-f")); }); });

  // 絞り込み中に市町を選んだときは、その市町が見えるように絞り込みを外す
  document.querySelectorAll(".pick-grid a, a[href='#statewide']").forEach(function (a) {
    a.addEventListener("click", function () {
      var t = document.getElementById(a.getAttribute("href").slice(1));
      if (t && t.closest(".card, .region") && (t.hidden || (t.closest(".region") || {}).hidden)) apply("all");
    });
  });
})();
</script>"""


def list_page(data, draft):
    checked = data["checked"]
    cities = data["cities"]
    regions = data["regions"]
    n_benefit = sum(1 for c in cities if c["k"] in HAS_BENEFIT)

    pick = []
    for r in regions:
        rows = [c for c in cities if c["r"] == r["id"]]
        links = "\n        ".join(
            f'<a href="#{c["slug"]}" data-name="{e(c["n"])}" data-yomi="{e(c["y"])}">{e(c["n"])}</a>'
            for c in rows)
        pick.append(f"""    <div class="pick-region">
      <h3>{e(r['name'])}</h3>
      <div class="pick-grid">
        {links}
      </div>
    </div>""")

    chips = []
    for fid, label, kinds in FILTERS:
        n = len(cities) if kinds is None else sum(1 for c in cities if c["k"] in kinds)
        pressed = "true" if fid == "all" else "false"
        chips.append(f'<button type="button" data-f="{fid}" aria-pressed="{pressed}">{e(label)}<span class="n">{n}</span></button>')

    sections = []
    for r in regions:
        rows = [c for c in cities if c["r"] == r["id"]]
        cards = "\n".join(card(c, checked) for c in rows)
        sections.append(f"""<section class="region" id="r-{r['id']}" aria-labelledby="r-{r['id']}-h">
  <div class="region-head">
    <h2 id="r-{r['id']}-h">{e(r['name'])}<span class="rc">{len(rows)}市町</span></h2>
    <a href="#pick">市町を選び直す ↑</a>
  </div>
{cards}
</section>""")

    legend = "\n".join(
        f'    <div><dt><span class="chip k-{k}">{e(v[0])}</span></dt><dd>{e(v[1])}</dd></div>'
        for k, v in KINDS.items())

    y, m, d = checked.split("-")
    main = f"""<nav class="crumbs" aria-label="いまいる場所"><a href="./">トップ</a> ＞ 兵庫県の免許返納特典</nav>
<div class="hero">
  <div class="hero-top">
    <p class="eyebrow">兵庫県・41市町</p>
    <div class="stamp" role="img" aria-label="{jdate(checked)}に確認"><span>確認</span><b>{y}</b><b>{int(m)}.{int(d)}</b></div>
  </div>
  <h1>運転免許を返納したら、何がもらえる？</h1>
  <p class="lead">兵庫県の41市町が、運転免許を自主返納した人に出している特典を、同じ項目にそろえて並べました。</p>
</div>

<section class="pick" id="pick" aria-labelledby="pick-h">
  <h2 class="section-title" id="pick-h">お住まいの市町を選んでください</h2>
  <div class="search">
    <label for="q">名前で探す <span class="hint">（ひらがなでも探せます）</span></label>
    <input id="q" type="search" autocomplete="off" placeholder="例：あかし、丹波">
  </div>
  <div class="pick-list" id="pick-list">
{chr(10).join(pick)}
  </div>
  <p class="pick-none" id="pick-none" hidden>見つかりませんでした。市や町の名前の一部を、ひらがなで入れてみてください。</p>
</section>

<section class="statewide" id="statewide" aria-labelledby="sw-h">
  <h2 id="sw-h">兵庫県内どこに住んでいても使える割引</h2>
  <p>65歳以上で「運転経歴証明書」を持っている人は、証明書を見せると、公共交通機関の運賃割引などを受けられます（証明書の住所が兵庫県の人に限ります）。高齢者運転免許自主返納サポート協議会に加わる企業・団体の特典で、一覧は兵庫県警のページで見られます。</p>
  <p>運転経歴証明書は、免許を返納したあとに申し込める証明書です。本人確認の書類としても使えます。</p>
  <p><a class="btn-src" href="https://www.police.pref.hyogo.lg.jp/traffic/license/keireki_tokuten/index.htm" target="_blank" rel="noopener">兵庫県警の特典一覧を見る<span aria-hidden="true">↗</span></a></p>
  <p class="src">出典：<a href="https://www.city.amagasaki.hyogo.jp/kurashi/ansin/anzen/1017223.html" target="_blank" rel="noopener">尼崎市のページ</a>（{jdate(checked)}に確認）</p>
</section>

<section class="list-head" aria-labelledby="list-h">
  <h2 class="section-title" id="list-h">41市町の特典</h2>
  <p class="summary">41市町のうち <strong>{n_benefit}市町</strong> で、返納した人が使える特典や支援が見つかりました。</p>
  <div class="filters" id="filters" role="group" aria-label="種類で絞り込む">
    {chr(10).join('    ' + c if i else c for i, c in enumerate(chips))}
  </div>
  <p class="count" id="count" aria-live="polite">41市町すべてを表示しています。</p>
</section>

{chr(10).join(sections)}

<section class="about-list" id="about-list" aria-labelledby="al-h">
  <h2 id="al-h">この一覧について</h2>
  <dl class="legend">
{legend}
  </dl>
  <ul class="bullets">
    <li>{jdate(checked)}に、41市町の公式ページを開いて、金額・対象の年齢・申し込み期限を原文で確かめました。神戸市と多可町は、それぞれのカードに書いた方法で確かめています。</li>
    <li>市町のページに書かれていないことは「記載なし」とし、推測で埋めていません。</li>
    <li>企業・団体の割引（公共交通機関の運賃割引など）は含めていません。<a href="#statewide">兵庫県内どこに住んでいても使える割引</a>から探せます。</li>
    <li>制度は変わることがあります。申し込む前に、市町の公式ページか窓口で確かめてください。</li>
    <li>間違いに気づいたら、<a href="about.html#contact">運営者情報</a>のページからお知らせください。</li>
  </ul>
</section>"""

    return shell(
        title="兵庫県の免許返納特典 41市町の一覧（2026年9月確認）｜じもとくらべ",
        description=f"兵庫県の41市町が、運転免許を自主返納した人に出している特典（ICOCA、タクシー券、バスの無料券など）を、金額・対象の年齢・申し込み期限をそろえて比べられます。{jdate(checked)}に各市町の公式ページで確認。",
        path="hyogo-menkyo-henno.html",
        main=main, draft=draft,
        draft_note="「記載なし」の11市町の扱いは、公開する前に決めます。",
        scripts=LIST_SCRIPT)


# ---------------- トップ ----------------

def top_page(data, draft):
    n_benefit = sum(1 for c in data["cities"] if c["k"] in HAS_BENEFIT)
    main = f"""<section class="top-hero">
  <h1 class="name">じもと<span>くらべ</span></h1>
  <p class="lead">住んでいる市や町によって、使える制度はちがいます。市町の公式ページを1つずつ開いて、同じ項目にそろえて並べています。</p>
</section>

<a class="topic" href="hyogo-menkyo-henno.html">
  <span class="t-eyebrow">兵庫県・41市町</span>
  <span class="t-title">運転免許を返納したら、何がもらえる？</span>
  <span class="t-meta">{n_benefit}市町で特典や支援が見つかりました ・ {jdate(data['checked'])}に確認</span>
  <span class="t-go">41市町の一覧を見る →</span>
</a>
<p class="next-note">ほかの制度も、順に追加していきます。</p>

<section class="about-list" aria-labelledby="how-h">
  <h2 id="how-h">調べ方</h2>
  <ul class="bullets">
    <li>市町の公式ページを開いて、原文で確かめます。</li>
    <li>確かめた日を、ページごとに書きます。</li>
    <li>ページに書かれていないことは「記載なし」とし、推測で埋めません。</li>
  </ul>
</section>"""
    return shell(
        title="じもとくらべ｜市や町ごとの制度を比べる",
        description="住んでいる市や町によってちがう制度を、公式ページで確かめて、同じ項目にそろえて比べられるサイトです。",
        path="", main=main, draft=draft)


# ---------------- 運営者情報 ----------------

def about_page(draft):
    main = """<article class="prose">
  <h1>運営者情報</h1>
  <section aria-label="基本の情報">
    <dl class="info">
      <div><dt>サイト名</dt><dd>じもとくらべ</dd></div>
      <div><dt>アドレス</dt><dd>https://jimotokurabe.jp/</dd></div>
      <div><dt>運営</dt><dd>個人で運営しています</dd></div>
      <div id="contact"><dt>連絡先</dt><dd>お問い合わせフォーム（準備中）</dd></div>
    </dl>
  </section>
  <section>
    <h2>このサイトについて</h2>
    <p>住んでいる市や町によって、使える制度はちがいます。けれども、市町ごとのページを1つずつ開いて比べるのは大変です。このサイトは、市町の公式ページで確かめた内容を、同じ項目にそろえて並べ、比べられるようにしています。</p>
  </section>
  <section>
    <h2>情報の調べ方</h2>
    <ul class="bullets">
      <li>市町の公式ページを開いて、原文で確かめます。</li>
      <li>確かめた日を、ページごとに書きます。</li>
      <li>ページに書かれていないことは「記載なし」とし、推測で埋めません。</li>
      <li>公式ページを原文で確かめられなかったときは、どう確かめたかを、その市町の欄に書きます。</li>
    </ul>
  </section>
  <section>
    <h2>間違いを見つけたら</h2>
    <p>内容の間違いや、制度が変わったことに気づいたら、お知らせください。確かめて直し、直した日をページに書きます。</p>
  </section>
  <section>
    <h2>広告について</h2>
    <p>いまは広告を載せていません。載せる場合も、広告の都合で内容を変えることはしません。</p>
  </section>
  <section>
    <h2>ご利用にあたって</h2>
    <p>掲載している情報は、確かめた日の時点のものです。制度は変わることがあるため、申し込む前に、市町の公式ページか窓口で確かめてください。このサイトの情報を使ったことで生じた損害について、責任を負いかねます。</p>
  </section>
  <p class="updated">2026年9月26日 作成</p>
</article>"""
    return shell(
        title="運営者情報｜じもとくらべ",
        description="じもとくらべの運営者と、情報の調べ方、間違いを見つけたときの連絡について。",
        path="about.html", main=main, draft=draft)


# ---------------- プライバシーポリシー ----------------

def privacy_page(draft):
    main = """<article class="prose">
  <h1>プライバシーポリシー</h1>
  <p>じもとくらべ（以下「このサイト」）で扱う情報について説明します。</p>
  <section>
    <h2>集める情報</h2>
    <p>このサイトには、会員登録や入力フォームはありません。アクセス解析や広告のためのCookieも、いまは使っていません。</p>
  </section>
  <section>
    <h2>外部のサービス</h2>
    <ul class="bullets">
      <li>文字の表示に Google Fonts を使っています。ページを開くと、文字のデータを受け取るためにGoogleのサーバーに接続するので、IPアドレスなどがGoogleに送られます。</li>
      <li>このサイトは GitHub Pages で公開しています。GitHubは、セキュリティのために、閲覧した人のIPアドレスを記録しています（<a href="https://docs.github.com/ja/pages/getting-started-with-github-pages/what-is-github-pages" target="_blank" rel="noopener">GitHubの説明</a>）。</li>
    </ul>
  </section>
  <section>
    <h2>文字の大きさの設定</h2>
    <p>「大きく」を選ぶと、その設定をお使いのブラウザの中に保存します。このサイトに送られることはありません。</p>
  </section>
  <section>
    <h2>お問い合わせでいただいた情報</h2>
    <p>お問い合わせでいただいた名前やメールアドレスは、返信のためだけに使い、ほかの目的には使いません。</p>
  </section>
  <section>
    <h2>このページの変更</h2>
    <p>内容を変えるときは、このページを書き換えて日付を更新します。アクセス解析や広告を始めるときは、始める前にこのページに書きます。</p>
  </section>
  <p class="updated">2026年9月26日 制定</p>
</article>"""
    return shell(
        title="プライバシーポリシー｜じもとくらべ",
        description="じもとくらべで扱う情報と、使っている外部のサービスについて。",
        path="privacy.html", main=main, draft=draft)


def to_artifact_fragment(doc, title):
    """サイト用の完全なHTMLから、確認用ページ（本文だけの形）を作る。"""
    head = re.search(r"<head>(.*?)</head>", doc, re.S).group(1)
    body = re.search(r"<body>(.*?)</body>", doc, re.S).group(1)
    keep = [l for l in head.splitlines()
            if l.startswith("<link rel=\"preconnect\"") or l.startswith("<link rel=\"stylesheet\"")
            or l.startswith("<script>try")]
    return f"<title>{e(title)}</title>\n" + "\n".join(keep) + "\n" + body.strip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT))
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--artifact")
    a = ap.parse_args()
    data = json.loads((ROOT / "data" / "hyogo-menkyo-henno.json").read_text(encoding="utf-8"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pages = {
        "index.html": top_page(data, a.draft),
        "hyogo-menkyo-henno.html": list_page(data, a.draft),
        "about.html": about_page(a.draft),
        "privacy.html": privacy_page(a.draft),
    }
    for name, html in pages.items():
        (out / name).write_text(html, encoding="utf-8")
    if out.resolve() != ROOT:
        shutil.copy(ROOT / "site.css", out / "site.css")
    if not a.draft:
        urls = ["", "hyogo-menkyo-henno.html", "about.html", "privacy.html"]
        (out / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "".join(f"  <url><loc>{SITE}{u}</loc></url>\n" for u in urls)
            + "</urlset>\n", encoding="utf-8")
        (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}sitemap.xml\n", encoding="utf-8")
    if a.artifact:
        art = Path(a.artifact)
        art.mkdir(parents=True, exist_ok=True)
        (art / "index.html").write_text(to_artifact_fragment(pages["index.html"], "じもとくらべ"), encoding="utf-8")
        for name in ("hyogo-menkyo-henno.html", "about.html", "privacy.html"):
            (art / name).write_text(pages[name], encoding="utf-8")
        shutil.copy(ROOT / "site.css", art / "site.css")
    print("built:", ", ".join(pages), "| draft" if a.draft else "")


if __name__ == "__main__":
    main()
