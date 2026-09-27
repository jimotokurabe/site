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
from urllib.parse import quote

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
# 高齢者のタクシー代の助成（data/hyogo-taxi.json）の区分
TAXI_KINDS = {
    "yes": ("助成あり", "年齢などの条件を満たす高齢者に、タクシー代を助成する"),
    "care": ("条件つき", "年齢だけでは使えず、介護の認定・体の状態・運転経歴証明書などの条件が要る（通院だけに使えるものも含む）"),
    "henno_only": ("返納者のみ", "運転免許を返納した人に限った助成で、免許返納の特典の一覧に載っている"),
    "end": ("終了", "以前はあったが、終わった"),
    "none": ("なし", "市町のページに「ない」と書かれている"),
    "notfound": ("記載なし", "市町のページに、高齢者向けのタクシー代の助成が見つからない。「ない」とも書かれていない"),
}
GUIDE_DIR = "hyogo-menkyo-henno"  # 市町ごとの手順ページを置くフォルダ（いまは兵庫県だけ）
HOME_PREF = "hyogo"  # トップ・最初のひと言・手順ページで使う県


def list_path(pref):
    return f"{pref['id']}-menkyo-henno.html"


def taxi_path(pref):
    return f"{pref['id']}-taxi.html"


def city_unit(name):
    return "町" if name.endswith("町") else "村" if name.endswith("村") else "市"
# お問い合わせ（Googleフォーム。2026-09-26 に、ログインなしで開けること・運営者のメールアドレスが載っていないことを確認）
CONTACT_URL = "https://docs.google.com/forms/d/e/1FAIpQLSeNJuZsE9F--Erk3ZQK5rMyP704VH8S4mW5BNll9z_t7BeREg/viewform"
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


def shell(*, title, description, path, main, draft, draft_note="", scripts="", base="", page_class=""):
    """base は、サイトの直下から見たこのページの位置（下の階層のページなら "../"）。"""
    canonical = SITE + path
    home = base or "./"
    wrap_class = f"wrap {page_class}".strip()
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
<link rel="stylesheet" href="{base}site.css">
{SIZE_BOOT}
</head>
<body>
<a class="skip" href="#main">本文へ移動</a>
<div class="{wrap_class}">
<header class="topbar">
  <a class="brand" href="{home}">じもと<span>くらべ</span></a>
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
    <a href="{home}">トップ</a>
    <a href="{base}about.html">運営者情報</a>
    <a href="{base}privacy.html">プライバシーポリシー</a>
    <a href="{CONTACT_URL}" target="_blank" rel="noopener">お問い合わせ</a>
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


def taxi_block(t, unit):
    """市町のカードの下に出す、高齢者のタクシー代の助成の欄。"""
    label = TAXI_KINDS[t["k"]][0]
    facts = ""
    if t["k"] in ("yes", "care"):
        facts += fact("対象", t.get("age"))
        facts += fact("助成の中身", t.get("amt"))
        facts += fact("申し込み", t.get("how"))
    link_back = t.get("henno_link")
    if link_back and link_back != "記載なし":
        facts += fact("返納した人は", link_back)
    parts = [f'<p>{e(t["what"])}</p>']
    if facts:
        parts.append(f'<dl class="facts">\n{facts}    </dl>')
    if t.get("note"):
        parts.append(f'<p class="note">{e(t["note"])}</p>')
    if t.get("flag"):
        parts.append(f'<p class="flag">確かめ方：{e(t["flag"])}</p>')
    if t.get("url"):
        src = t.get("src") or f"{unit}の公式ページ"
        link = (f'<a class="btn-src" href="{e(t["url"])}" target="_blank" rel="noopener">'
                f'{e(src)}を見る<span aria-hidden="true">↗</span></a>')
        dates = f'ページの日付：{e(t.get("upd") or "記載なし")}<br>確かめた日：{jdate(t["checked"])}'
    else:
        link = f'<span class="empty-src">{unit}の公式ページ：見つかりませんでした</span>'
        dates = f'確かめた日：{jdate(t["checked"])}'
    parts.append(f'<div class="card-foot">\n      {link}\n      <p class="dates">{dates}</p>\n    </div>')
    body = "\n    ".join(parts)
    return f"""<section class="taxi" aria-label="高齢者のタクシー代の助成">
    <div class="taxi-head">
      <h4>高齢者のタクシー代の助成</h4>
      <span class="chip t-{t['k']}">{e(label)}</span>
    </div>
    {body}
  </section>"""


def card(c, checked, taxi=None, statewide=True, hk_link=True):
    kind_label = KINDS[c["k"]][0]
    unit = city_unit(c["n"])
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
        more = '<a href="#statewide">県内どこでも使える割引</a>もあります。' if statewide else ""
        parts.append(f'<p class="note">くわしくは{unit}の窓口で確かめてください。{more}</p>')
    if c.get("flag"):
        parts.append(f'<p class="flag">確かめ方：{e(c["flag"])}</p>')
    if c.get("guide"):
        label = c["guide"].get("link_label", "返納から申し込みまでの手順を見る")
        parts.append(f'<p><a class="btn-guide" href="{GUIDE_DIR}/{c["slug"]}.html">'
                     f'{e(label)}<span aria-hidden="true">→</span></a></p>')
    if c.get("url"):
        src = c.get("src") or f"{unit}の公式ページ"
        link = (f'<a class="btn-src" href="{e(c["url"])}" target="_blank" rel="noopener">'
                f'{e(src)}を見る<span aria-hidden="true">↗</span></a>')
        dates = f'ページの日付：{e(c["upd"])}<br>確かめた日：{jdate(checked)}'
    else:
        link = f'<span class="empty-src">{unit}の公式ページ：見つかりませんでした</span>'
        dates = f'確かめた日：{jdate(checked)}'
    parts.append(f'<div class="card-foot">\n    {link}\n    <p class="dates">{dates}</p>\n  </div>')
    if hk_link:
        parts.append(f'<p class="to-hk"><a href="{HANASHI_PATH}?city={c["slug"]}">親に話すときの、最初のひと言<span aria-hidden="true"> →</span></a></p>')
    henno_body = "\n    ".join(parts)
    blocks = [f"""<section class="henno-part" aria-label="免許返納の特典">
    <div class="part-head">
      <h4>免許返納の特典</h4>
      <span class="chip k-{c['k']}">{e(kind_label)}</span>
    </div>
    {henno_body}
  </section>"""]
    t = (taxi or {}).get(c["slug"])
    if t:
        blocks.append(taxi_block(t, unit))
    body = "\n  ".join(blocks)
    notfound = " is-notfound" if c["k"] == "notfound" else ""
    tk = f' data-taxi="{t["k"]}"' if t else ""
    return f"""<article class="card{notfound}" id="{c['slug']}" data-k="{c['k']}"{tk} aria-labelledby="{c['slug']}-h">
  <div class="card-head">
    <h3 class="city" id="{c['slug']}-h">{e(c['n'])}<span class="yomi">{e(c['y'])}</span></h3>
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
  var SETS = { endnone: ["end", "none", "henno_only"] };
  function apply(f) {
    var shown = 0;
    chips.forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-f") === f)); });
    cards.forEach(function (c) {
      var k = c.getAttribute("data-k");
      var hit = f === "all" || (f === "taxi" ? c.getAttribute("data-taxi") === "yes"
        : f === "henno" ? c.hasAttribute("data-henno")
        : SETS[f] ? SETS[f].indexOf(k) >= 0 : k === f);
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


def pick_html(data, href_prefix=""):
    """地域ごとの市町ボタン。href_prefix を付けると、ほかのページの市町の欄へ飛ぶ。"""
    out = []
    for r in data["regions"]:
        rows = [c for c in data["cities"] if c["r"] == r["id"]]
        links = "\n        ".join(
            f'<a href="{href_prefix}#{c["slug"]}" data-name="{e(c["n"])}" data-yomi="{e(c["y"])}">{e(c["n"])}</a>'
            for c in rows)
        out.append(f"""    <div class="pick-region">
      <h3>{e(r['name'])}</h3>
      <div class="pick-grid">
        {links}
      </div>
    </div>""")
    return "\n".join(out)


# 市町の名前で探す（一覧とトップで共通）
PICK_SCRIPT = """<script>
(function () {
  function norm(s) {
    return String(s).normalize("NFKC")
      .replace(/[\\u30a1-\\u30f6]/g, function (c) { return String.fromCharCode(c.charCodeAt(0) - 0x60); })
      .replace(/\\s+/g, "").toLowerCase();
  }
  var q = document.getElementById("q");
  if (!q) return;
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
})();
</script>"""


# 一覧の冒頭に出す「最初のひと言」の見本（タイプ・場面ごとに1つずつ。data/hanashikata.json の文をそのまま使う）
HK_SAMPLES = [("pride", "renew"), ("life", "money"), ("ready", "family")]


def hk_banner(hk):
    if not hk:
        return ""
    samples = [{"type": hk["types"][t]["name"], "trig": hk["triggers"][g], "text": hk["phrases"][t][g][0]}
               for t, g in HK_SAMPLES]
    first = samples[0]
    data_attr = e(json.dumps(samples, ensure_ascii=False))
    return f"""<aside class="hk-banner" aria-labelledby="hkb-h" data-samples="{data_attr}">
    <p class="hkb-eyebrow">家族のための道具</p>
    <h2 id="hkb-h">親にどう話しはじめるか、迷ったら</h2>
    <p class="hkb-lead">6つの質問に答えると、親御さんのタイプと場面に合った「最初のひと言」が出ます。たとえば、こんな感じです。</p>
    <figure class="hkb-sample">
      <figcaption><span class="hkb-type">{e(first["type"])}</span><span class="hkb-trig">{e(first["trig"])}</span></figcaption>
      <blockquote>「{e(first["text"])}」</blockquote>
    </figure>
    <p class="hkb-actions">
      <a class="hkb-go" href="{HANASHI_PATH}">質問に答えて、ひと言を見る<span aria-hidden="true"> →</span></a>
      <button type="button" class="hkb-next" hidden>ほかの例</button>
    </p>
  </aside>"""


HK_BANNER_SCRIPT = """<script>
(function () {
  var b = document.querySelector(".hk-banner");
  if (!b) return;
  var s = JSON.parse(b.getAttribute("data-samples")), i = 0, btn = b.querySelector(".hkb-next");
  btn.hidden = false;
  btn.addEventListener("click", function () {
    i = (i + 1) % s.length;
    b.querySelector(".hkb-type").textContent = s[i].type;
    b.querySelector(".hkb-trig").textContent = s[i].trig;
    b.querySelector("blockquote").textContent = "「" + s[i].text + "」";
  });
})();
</script>"""


def list_page(data, draft):
    P = data["pref"]
    pn, pu = P["name"], P["unit"]
    sw = P.get("statewide")
    home = P["id"] == HOME_PREF
    checked = data["checked"]
    cities = data["cities"]
    regions = data["regions"]
    total = len(cities)
    n_benefit = sum(1 for c in cities if c["k"] in HAS_BENEFIT)
    taxi = data.get("taxi", {})
    n_taxi = sum(1 for t in taxi.values() if t["k"] == "yes")

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
    if taxi:
        chips.append(f'<button type="button" data-f="taxi" aria-pressed="false">タクシー代の助成あり<span class="n">{n_taxi}</span></button>')

    sections = []
    for r in regions:
        rows = [c for c in cities if c["r"] == r["id"]]
        cards = "\n".join(card(c, checked, taxi, statewide=bool(sw), hk_link=home) for c in rows)
        sections.append(f"""<section class="region" id="r-{r['id']}" aria-labelledby="r-{r['id']}-h">
  <div class="region-head">
    <h2 id="r-{r['id']}-h">{e(r['name'])}<span class="rc">{len(rows)}{pu}</span></h2>
    <a href="#pick">{pu}を選び直す ↑</a>
  </div>
{cards}
</section>""")

    legend = "\n".join(
        f'    <div><dt><span class="chip k-{k}">{e(v[0])}</span></dt><dd>{e(v[1])}</dd></div>'
        for k, v in KINDS.items())
    taxi_legend = taxi_note = ""
    if taxi:
        rows_t = "\n".join(
            f'    <div><dt><span class="chip t-{k}">{e(v[0])}</span></dt><dd>{e(v[1])}</dd></div>'
            for k, v in TAXI_KINDS.items())
        taxi_legend = f'  <h3>高齢者のタクシー代の助成の区分</h3>\n  <dl class="legend">\n{rows_t}\n  </dl>\n'
        taxi_note = (f'    <li>高齢者のタクシー代の助成は、{jdate(data["taxi_checked"])}に{total}{pu}の公式ページで確かめました。'
                     '年齢や介護の認定などを条件にしたものを載せ、障害者手帳だけが条件の福祉タクシー券は含めていません。'
                     '原文で確かめきれなかった点は、その市町の欄に書いています。</li>\n')
    taxi_lead = (f'返納したあとの移動に使える、高齢者のタクシー代の助成もあわせて載せています'
                 f'（<a href="{taxi_path(P)}">タクシー代の助成だけの一覧</a>）。') if taxi else ""
    taxi_summary = f"高齢者のタクシー代の助成は <strong>{n_taxi}{pu}</strong> で見つかりました。" if taxi else ""
    sw_html = ""
    if sw:
        body = "\n".join(f"  <p>{e(b)}</p>" for b in sw["body"])
        sw_html = f"""
<section class="statewide" id="statewide" aria-labelledby="sw-h">
  <h2 id="sw-h">{e(sw['title'])}</h2>
{body}
  <p><a class="btn-src" href="{e(sw['link_url'])}" target="_blank" rel="noopener">{e(sw['link_label'])}<span aria-hidden="true">↗</span></a></p>
  <p class="src">出典：<a href="{e(sw['src_url'])}" target="_blank" rel="noopener">{e(sw['src_label'])}</a>（{jdate(checked)}に確認）</p>
</section>
"""
        sw_bullet = f'<a href="#statewide">{e(sw["title"])}</a>から探せます。'
    else:
        sw_bullet = "県警のページで探せます。"

    y, m, d = checked.split("-")
    flagged_names = [c["n"] for c in cities if c.get("flag")]
    flagged = f"{'と'.join(flagged_names)}は、カードに書いた方法で確かめています。" if flagged_names else ""
    main = f"""<nav class="crumbs" aria-label="いまいる場所"><a href="./">トップ</a> ＞ {pn}の免許返納特典</nav>
<div class="hero">
  <div class="hero-top">
    <p class="eyebrow">{pn}・{total}{pu}</p>
    <div class="stamp" role="img" aria-label="{jdate(checked)}に確認"><span>確認</span><b>{y}</b><b>{int(m)}.{int(d)}</b></div>
  </div>
  <h1>運転免許を返納したら、何がもらえる？</h1>
  <p class="lead">{pn}の{total}{pu}が、運転免許を自主返納した人に出している特典を、同じ項目にそろえて並べました。{taxi_lead}</p>
{hk_banner(data.get("hk")) if home else ""}
</div>

<section class="pick" id="pick" aria-labelledby="pick-h">
  <h2 class="section-title" id="pick-h">お住まいの{pu}を選んでください</h2>
  <div class="search">
    <label for="q">名前で探す <span class="hint">（ひらがなでも探せます）</span></label>
    <input id="q" type="search" autocomplete="off" placeholder="{e(P.get('placeholder', '例：あかし、丹波'))}">
  </div>
  <div class="pick-list" id="pick-list">
{chr(10).join(pick)}
  </div>
  <p class="pick-none" id="pick-none" hidden>見つかりませんでした。市や町の名前の一部を、ひらがなで入れてみてください。</p>
</section>
{sw_html}
<section class="list-head" aria-labelledby="list-h">
  <h2 class="section-title" id="list-h">{total}{pu}の特典</h2>
  <p class="summary">{total}{pu}のうち <strong>{n_benefit}{pu}</strong> で、返納した人が使える特典や支援が見つかりました。{taxi_summary}</p>
  <div class="filters" id="filters" role="group" aria-label="種類で絞り込む">
    {chr(10).join('    ' + c if i else c for i, c in enumerate(chips))}
  </div>
  <p class="count" id="count" aria-live="polite">{total}{pu}すべてを表示しています。</p>
</section>

{chr(10).join(sections)}

<section class="about-list" id="about-list" aria-labelledby="al-h">
  <h2 id="al-h">この一覧について</h2>
  <dl class="legend">
{legend}
  </dl>
{taxi_legend}  <ul class="bullets">
    <li>{jdate(checked)}に、{total}{pu}の公式ページを開いて、金額・対象の年齢・申し込み期限を原文で確かめました。{flagged}</li>
    <li>{pu}のページに書かれていないことは「記載なし」とし、推測で埋めていません。</li>
{taxi_note}    <li>企業・団体の割引（公共交通機関の運賃割引など）は含めていません。{sw_bullet}</li>
    <li>制度は変わることがあります。申し込む前に、{pu}の公式ページか窓口で確かめてください。</li>
    <li>間違いに気づいたら、<a href="{CONTACT_URL}" target="_blank" rel="noopener">お問い合わせフォーム</a>からお知らせください。</li>
  </ul>
</section>"""

    return shell(
        title=(f"{pn}の免許返納特典{'と高齢者タクシー助成' if taxi else ''} {total}{pu}の一覧（{int(y)}年{int(m)}月確認）｜じもとくらべ"),
        description=(f"{pn}の{total}{pu}が、運転免許を自主返納した人に出している特典（ICOCA、タクシー券、バスの無料券など）"
                     + ("と、高齢者のタクシー代の助成を、金額・対象の年齢をそろえて" if taxi else "を、金額・対象の年齢・申し込み期限をそろえて")
                     + f"比べられます。{jdate(checked)}に各市町の公式ページで確認。"),
        path=list_path(P),
        main=main, draft=draft,
        draft_note=P.get("draft_note", ""),
        scripts=LIST_SCRIPT + (HK_BANNER_SCRIPT if home else ""))


# ---------------- 高齢者のタクシー代の助成の一覧 ----------------

TAXI_FILTERS = [
    ("all", "すべて", None),
    ("yes", "助成あり", {"yes"}),
    ("care", "条件つき", {"care"}),
    ("henno", "返納すると早く使える", None),
    ("notfound", "記載なし", {"notfound"}),
    ("endnone", "終了・返納者のみ", {"end", "none", "henno_only"}),
]


def henno_earlier(t):
    """返納した人は、ほかの人より若い年齢などで使える（データの henno_earlier）。"""
    return t["k"] == "yes" and t.get("henno_earlier", False)


def taxi_card(c, t, P):
    unit = city_unit(c["n"])
    label = TAXI_KINDS[t["k"]][0]
    facts = ""
    if t["k"] in ("yes", "care"):
        facts += fact("対象", t.get("age"))
        facts += fact("助成の中身", t.get("amt"))
        facts += fact("申し込み", t.get("how"))
    h = t.get("henno_link")
    if h and h != "記載なし":
        facts += fact("返納した人は", h)
    parts = [f'<p class="what">{e(t["what"])}</p>']
    if t.get("name"):
        parts.append(f'<p class="note">制度の名前：{e(t["name"])}</p>')
    if facts:
        parts.append(f'<dl class="facts">\n{facts}  </dl>')
    if t.get("note"):
        parts.append(f'<p class="note">{e(t["note"])}</p>')
    if t.get("flag"):
        parts.append(f'<p class="flag">確かめ方：{e(t["flag"])}</p>')
    parts.append(f'<p class="note"><a href="{list_path(P)}#{c["slug"]}">{e(c["n"])}の免許返納の特典も見る</a></p>')
    if t.get("url"):
        src = t.get("src") or f"{unit}の公式ページ"
        link = (f'<a class="btn-src" href="{e(t["url"])}" target="_blank" rel="noopener">'
                f'{e(src)}を見る<span aria-hidden="true">↗</span></a>')
        dates = f'ページの日付：{e(t.get("upd") or "記載なし")}<br>確かめた日：{jdate(t["checked"])}'
    else:
        link = f'<span class="empty-src">{unit}の公式ページ：見つかりませんでした</span>'
        dates = f'確かめた日：{jdate(t["checked"])}'
    parts.append(f'<div class="card-foot">\n    {link}\n    <p class="dates">{dates}</p>\n  </div>')
    body = "\n  ".join(parts)
    notfound = " is-notfound" if t["k"] == "notfound" else ""
    henno = " data-henno" if henno_earlier(t) else ""
    return f"""<article class="card{notfound}" id="{c['slug']}" data-k="{t['k']}"{henno} aria-labelledby="{c['slug']}-h">
  <div class="card-head">
    <h3 class="city" id="{c['slug']}-h">{e(c['n'])}<span class="yomi">{e(c['y'])}</span></h3>
    <span class="chip t-{t['k']}">{e(label)}</span>
  </div>
  {body}
</article>"""


def taxi_page(data, draft):
    P = data["pref"]
    pn, pu = P["name"], P["unit"]
    taxi = data["taxi"]
    checked = data["taxi_checked"]
    cities = data["cities"]
    regions = data["regions"]
    total = len(cities)
    n_yes = sum(1 for t in taxi.values() if t["k"] == "yes")
    n_care = sum(1 for t in taxi.values() if t["k"] == "care")
    n_henno = sum(1 for t in taxi.values() if henno_earlier(t))

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
    for fid, label, kinds in TAXI_FILTERS:
        if fid == "henno":
            n = n_henno
        else:
            n = len(cities) if kinds is None else sum(1 for t in taxi.values() if t["k"] in kinds)
        pressed = "true" if fid == "all" else "false"
        chips.append(f'<button type="button" data-f="{fid}" aria-pressed="{pressed}">{e(label)}<span class="n">{n}</span></button>')

    sections = []
    for r in regions:
        rows = [c for c in cities if c["r"] == r["id"]]
        cards = "\n".join(taxi_card(c, taxi[c["slug"]], P) for c in rows)
        sections.append(f"""<section class="region" id="r-{r['id']}" aria-labelledby="r-{r['id']}-h">
  <div class="region-head">
    <h2 id="r-{r['id']}-h">{e(r['name'])}<span class="rc">{len(rows)}{pu}</span></h2>
    <a href="#pick">{pu}を選び直す ↑</a>
  </div>
{cards}
</section>""")

    legend = "\n".join(
        f'    <div><dt><span class="chip t-{k}">{e(v[0])}</span></dt><dd>{e(v[1])}</dd></div>'
        for k, v in TAXI_KINDS.items() if k != "none")
    flagged = "・".join(c["n"] for c in cities if taxi[c["slug"]].get("flag"))
    y, m, d = checked.split("-")
    main = f"""<nav class="crumbs" aria-label="いまいる場所"><a href="./">トップ</a> ＞ {pn}の高齢者のタクシー代の助成</nav>
<div class="hero">
  <div class="hero-top">
    <p class="eyebrow">{pn}・{total}{pu}</p>
    <div class="stamp" role="img" aria-label="{jdate(checked)}に確認"><span>確認</span><b>{y}</b><b>{int(m)}.{int(d)}</b></div>
  </div>
  <h1>高齢者のタクシー代、市や町が助成してくれる？</h1>
  <p class="lead">{pn}の{total}{pu}が、高齢者に出しているタクシー券やタクシー代の助成を、対象の年齢・金額・申し込み先をそろえて並べました。</p>
</div>

<section class="pick" id="pick" aria-labelledby="pick-h">
  <h2 class="section-title" id="pick-h">お住まいの{pu}を選んでください</h2>
  <div class="search">
    <label for="q">名前で探す <span class="hint">（ひらがなでも探せます）</span></label>
    <input id="q" type="search" autocomplete="off" placeholder="{e(P.get('taxi_placeholder', '例：さんだ、丹波'))}">
  </div>
  <div class="pick-list" id="pick-list">
{chr(10).join(pick)}
  </div>
  <p class="pick-none" id="pick-none" hidden>見つかりませんでした。市や町の名前の一部を、ひらがなで入れてみてください。</p>
</section>

<section class="list-head" aria-labelledby="list-h">
  <h2 class="section-title" id="list-h">{total}{pu}のタクシー代の助成</h2>
  <p class="summary">年齢などの条件で使える助成は <strong>{n_yes}{pu}</strong>、介護の認定などが要る助成は <strong>{n_care}{pu}</strong> で見つかりました。そのうち <strong>{n_henno}{pu}</strong> は、運転免許を返納すると、ほかの人より若い年齢などで使えます。</p>
  <div class="filters" id="filters" role="group" aria-label="種類で絞り込む">
    {chr(10).join('    ' + c if i else c for i, c in enumerate(chips))}
  </div>
  <p class="count" id="count" aria-live="polite">{total}{pu}すべてを表示しています。</p>
</section>

{chr(10).join(sections)}

<section class="about-list" id="about-list" aria-labelledby="al-h">
  <h2 id="al-h">この一覧について</h2>
  <dl class="legend">
{legend}
  </dl>
  <ul class="bullets">
    <li>{jdate(checked)}に、{total}{pu}の公式ページを開いて、対象・金額・申し込み先を原文で確かめました。</li>
    <li>年齢や介護の認定などを条件にしたものを載せています。障害者手帳だけが条件の福祉タクシー券は含めていません。</li>
    <li>予約して乗る乗合タクシー（デマンド交通）の、高齢者向けの料金の助成も含めています。</li>
    <li>{pu}のページに書かれていないことは「記載なし」とし、推測で埋めていません。原文で確かめきれなかった点は、その{pu}の欄に書いています（{flagged}）。</li>
    <li>運転免許を返納した人への特典は、<a href="{list_path(P)}">免許返納の特典の一覧</a>にあります。</li>
    <li>制度は変わることがあります。申し込む前に、{pu}の公式ページか窓口で確かめてください。</li>
    <li>間違いに気づいたら、<a href="{CONTACT_URL}" target="_blank" rel="noopener">お問い合わせフォーム</a>からお知らせください。</li>
  </ul>
</section>"""
    return shell(
        title=f"{pn}の高齢者タクシー助成 {total}{pu}の一覧（{int(y)}年{int(m)}月確認）｜じもとくらべ",
        description=(f"{pn}の{total}{pu}が高齢者に出しているタクシー券・タクシー代の助成を、対象の年齢・金額・申し込み先をそろえて比べられます。"
                     f"{n_yes}{pu}で年齢などで使える助成あり。{jdate(checked)}に各市町の公式ページで確認。"),
        path=taxi_path(P),
        main=main, draft=draft,
        scripts=LIST_SCRIPT)


# ---------------- 市町ごとの手順ページ ----------------

CITY_SCRIPT = """<script>
(function () {
  var printBtn = document.querySelector("[data-print]");
  if (printBtn) printBtn.addEventListener("click", function () { window.print(); });

  var copyBtn = document.querySelector("[data-copy]");
  var msg = document.getElementById("copied");
  var box = document.getElementById("copy-url");
  if (copyBtn) copyBtn.addEventListener("click", function () {
    var url = copyBtn.getAttribute("data-copy");
    function fallback() {
      box.hidden = false;
      box.focus();
      box.select();
      msg.textContent = "自動でコピーできませんでした。下のURLを長押しして、コピーしてください。";
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(function () {
        msg.textContent = "URLをコピーしました。LINEやメールに貼りつけて送れます。";
      }, fallback);
    } else {
      fallback();
    }
  });
})();
</script>"""

# 申し込み期限の計算（計算欄があるページだけに入れる）
CALC_SCRIPT = """<script>
(function () {
  // 申し込み期限の計算：「返納から1年以内」なら、1年後の同じ日の前の日を出す（どう数えても間に合う日）
  var calc = document.getElementById("deadline");
  if (calc) {
    var input = document.getElementById("calc-date");
    var out = document.getElementById("calc-out");
    var A = function (k) { return calc.getAttribute("data-" + k) || ""; };
    var years = parseInt(A("years"), 10) || 0, months = parseInt(A("months"), 10) || 0;
    var WD = "日月火水木金土";
    var parse = function (s) {
      var m = /^(\\d{4})-(\\d{2})-(\\d{2})$/.exec(s);
      return m ? new Date(+m[1], +m[2] - 1, +m[3]) : null;
    };
    var ymd = function (d) { return d.getFullYear() + "年" + (d.getMonth() + 1) + "月" + d.getDate() + "日"; };
    var ymdw = function (d) { return ymd(d) + "（" + WD.charAt(d.getDay()) + "）"; };
    var earliest = parse(A("earliest")), end = parse(A("end"));
    var period = "「" + A("period") + "」", ask = A("office") + "（" + A("tel") + "）";
    var show = function (state, lines) {
      out.textContent = "";
      lines.forEach(function (t, i) {
        var el = document.createElement(i ? "span" : "strong");
        el.textContent = t;
        out.appendChild(el);
      });
      calc.setAttribute("data-state", state);
      calc.classList.toggle("has-result", state !== "");
    };
    var update = function () {
      var d = parse(input.value);
      if (!d) return show("", ["日付を入れると、申し込みの期限が出ます。"]);
      var from = A("label") + "：" + ymdw(d);
      if (earliest && d < earliest)
        return show("ng", ["対象になりません", from, ymd(earliest) + "より前に返納した人は、対象ではありません。"]);
      if (end && d > end)
        return show("ng", ["期限を出せません", from, A("end-label") + "は" + ymd(end) + "までです。そのあとに返納する人が対象になるかは、" + A("unit") + "のページに書かれていません。"]);
      var total = d.getMonth() + years * 12 + months;
      var y = d.getFullYear() + Math.floor(total / 12), mo = total % 12;
      var limit = new Date(y, mo, Math.min(d.getDate(), new Date(y, mo + 1, 0).getDate()) - 1);
      var byEnd = !!(end && end < limit);
      if (byEnd) limit = end;
      var now = new Date(), today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      var left = Math.round((limit - today) / 86400000);
      if (left < 0 && byEnd)
        return show("ng", [A("end-label") + "は" + ymd(end) + "で終わりました", from, "次の年度も続くかは、" + A("unit") + "のページか" + ask + "で確かめてください。"]);
      if (left < 0)
        return show("ng", [ymdw(limit) + "を過ぎています", from, period + "に間に合うかは、" + ask + "に確かめてください。"]);
      show("ok", ["申し込みの期限：" + ymdw(limit) + (left === 0 ? "（今日まで）" : "（あと" + left + "日）"), from,
        byEnd ? period + "の日付より前に、" + A("end-label") + "が" + ymd(end) + "で終わるためです。"
              : "この日までに申し込めば、" + period + "に入ります。"]);
    };
    input.addEventListener("input", update);
    input.addEventListener("change", update);
    calc.hidden = false;
    document.querySelectorAll(".calc-link").forEach(function (el) { el.hidden = false; });
    update();
  }
})();
</script>"""

# 警察での手続きの持ち物（兵庫県警「運転経歴証明書申請手続き」で確認）
POLICE_CHECKLIST = [
    "運転免許証（マイナ免許証も持っている人は、両方）",
    "運転経歴証明書もつくるなら：手数料と写真（更新センターで本人が申し込むなら、写真は要りません）",
    "印鑑（運転経歴証明書を受け取るときにあると便利。サインでもかまいません）",
    "家族が代わりに行くなら：委任状兼承諾書、代理人誓約書、行く人の身分証明書",
]


def tel(num):
    return f'<a class="tel" href="tel:{num.replace("-", "")}">{e(num)}</a>'


def ext(url, label):
    return (f'<a class="btn-src" href="{e(url)}" target="_blank" rel="noopener">'
            f'{e(label)}<span aria-hidden="true">↗</span></a>')


def lis(items, indent):
    return "\n".join(f"{indent}<li>{e(x)}</li>" for x in items)


def checks(items):
    return "\n".join(f'      <label><input type="checkbox"> <span>{e(x)}</span></label>' for x in items)


def place_card(p):
    hours = "".join(f"<li>{e(h)}</li>" for h in p["hours"])
    phone = f"\n          <span>電話 {tel(p['tel'])}</span>" if p.get("tel") else ""
    where = f'\n          <span class="where">{e(p["where"])}</span>' if p.get("where") else ""
    return f"""        <div class="place">
          <b>{e(p['name'])}</b>{phone}
          <ul>{hours}</ul>{where}
        </div>"""


def deadline_calc(dl, ap, unit="市"):
    """返納した日から申し込み期限を出す欄。JavaScript が動くときだけ見せる（hidden を外す）。"""
    return f"""
      <div class="calc" id="deadline" hidden data-label="{e(dl['label'])}" data-years="{dl.get('years', 0)}" data-months="{dl.get('months', 0)}"
           data-period="{e(dl['period'])}" data-earliest="{e(dl.get('earliest', ''))}" data-end="{e(dl.get('end', ''))}"
           data-end-label="{e(dl.get('end_label', ''))}" data-office="{e(ap['office'])}" data-tel="{e(ap['tel'])}"
           data-unit="{unit}">
        <h4>申し込みの期限を調べる</h4>
        <label for="calc-date">{e(dl['label'])}を入れてください<span class="hint">{e(dl['hint'])}</span></label>
        <input type="date" id="calc-date">
        <p class="calc-out" id="calc-out" aria-live="polite">日付を入れると、申し込みの期限が出ます。</p>
        <ul class="bullets small">
{lis(dl.get('notes', []), '          ')}
        </ul>
      </div>"""


def contact_row(label, who, number=""):
    """who は名前1つか、[名前, 電話] の組のリスト（窓口が複数あるとき）。"""
    if isinstance(who, list):
        value = "<br>".join(f"{e(n)} {tel(t)}" for n, t in who)
    else:
        value = f"{e(who)} {tel(number)}" if number else e(who)
    return f"    <div><dt>{e(label)}</dt><dd>{value}</dd></div>\n"


def city_page(c, data, draft, base="../"):
    g = c["guide"]
    cm = data["common"]
    hn, kr, tk = cm["hennou"], cm["keireki"], cm["tokuten"]
    ap = g.get("apply")  # 市町に申し込む特典があるときだけ
    name = c["n"]
    unit = "町" if name.endswith("町") else "市"
    path = f"{GUIDE_DIR}/{c['slug']}.html"
    url = SITE + path
    checked = g["checked"]
    y, m, d = checked.split("-")

    # 手順1：警察で返納する
    places = "\n".join(place_card(p) for p in g["return_places"])
    receive = g.get("receive_note") or f"申請による運転免許の取消通知書（{unit}への申し込みに使うので、なくさないでください）"
    stations = ""
    if g.get("stations"):
        rows = "\n".join(f'            <tr><th scope="row">{e(n)}</th><td>{e(area)}</td><td>{tel(t)}</td></tr>'
                         for n, area, t in g["stations"])
        stations = f"""
      <details class="more">
        <summary>{e(name)}内の警察署と電話番号</summary>
        <div class="table-scroll">
          <table class="list-table">
            <thead><tr><th scope="col">警察署</th><th scope="col">ある場所</th><th scope="col">電話</th></tr></thead>
            <tbody>
{rows}
            </tbody>
          </table>
        </div>
        <p class="src-line">どの警察署がどの地域を受け持つかは、<a href="{e(hn['stations_url'])}" target="_blank" rel="noopener">兵庫県警の警察署一覧</a>から、各警察署のページで確かめられます。</p>
      </details>"""

    # 手順2：運転経歴証明書
    step2_title = g.get("step2_title", "運転経歴証明書をつくるか決める")
    if g.get("step2_lead"):
        step2_lead = e(g["step2_lead"])
    else:
        step2_lead = (f"つくらなくても、{e(name)}の特典はもらえます。つくると、65歳以上なら"
                      '<a href="#statewide">県内どこでも使える割引</a>を受けられます。')
    fees = "\n".join(f'          <tr><th scope="row">{e(k)}</th><td>{e(v)}</td></tr>' for k, v in kr["fees"])

    # 手順3：市町に申し込む／割引などを使う
    if ap:
        deadline = dict(g["facts"]).get("申し込み期限", "")
        ways = "\n".join(f"        <li><b>{e(k)}：</b>{e(v)}</li>" for k, v in ap["ways"])
        calc = deadline_calc(ap["deadline"], ap, unit) if ap.get("deadline") else ""
        more = "".join(f"""
      <details class="more">
        <summary>{e(m['summary'])}</summary>
        <ul class="bullets">
{lis(m['items'], '          ')}
        </ul>
      </details>""" for m in ap.get("more", []))
        # まとめにも同じ期限があるので、印刷では手順3の側を出さない
        dup_deadline = fact("申し込み期限", deadline).replace("<div>", '<div class="no-print">', 1)
        links = [ext(ap["form_url"], ap.get("form_label", "申請用紙（PDF）を開く"))] if ap.get("form_url") else []
        links += [ext(u, label) for u, label in ap.get("links", [])]
        link_row = f'\n      <p class="src-links">{" ".join(links)}</p>' if links else ""
        step3 = f"""    <li class="step" id="step-3">
      <h3><span class="num" aria-hidden="true">3</span>{e(name)}に申し込む</h3>
      <p>{e(ap['write'])}{e(ap.get('choice_note', ''))}</p>
      <dl class="facts">
{fact(ap.get("attach_label", "添えるもの"), ap['attach'])}{dup_deadline}{fact(ap.get("address_label", "宛先"), ap['address'])}        <div><dt>問い合わせ</dt><dd>{e(ap['office'])} {tel(ap['tel'])}</dd></div>
      </dl>{calc}
      <ul class="bullets">
{ways}
      </ul>
      <p class="note">{e(ap['proxy'])}</p>{more}{link_row}
    </li>"""
    else:
        use = g["use"]
        items = "\n".join(
            f'        <li><b>{e(head)}</b><br>{e(body)}（<a href="{e(href)}">「{e(label)}」を見る</a>）</li>'
            for head, body, href, label in use["items"])
        step3 = f"""    <li class="step" id="step-3">
      <h3><span class="num" aria-hidden="true">3</span>{e(use['title'])}</h3>
      <ul class="bullets">
{items}
      </ul>
    </li>"""

    fieldsets = [f"""    <fieldset>
      <legend>警察へ（手順1・2）</legend>
{checks(POLICE_CHECKLIST)}
    </fieldset>"""]
    if ap:
        fieldsets.append(f"""    <fieldset>
      <legend>{e(name)}へ（手順3）</legend>
{checks(ap['checklist'])}
    </fieldset>""")

    # 市町の制度のくわしい説明。1つなら extra_title・extra・extra_src、2つ以上なら extras に並べる
    extras = g.get("extras") or []
    if g.get("extra"):
        extras = [{"id": "extra", "title": g["extra_title"], "items": g["extra"], "src": g["extra_src"]}]
    extra = "".join(f"""
<section class="block extra" id="{e(x['id'])}" aria-labelledby="{'ex' if x['id'] == 'extra' else e(x['id'])}-h">
  <h2 id="{'ex' if x['id'] == 'extra' else e(x['id'])}-h">{e(x['title'])}</h2>
  <ul class="bullets">
{lis(x['items'], '    ')}
  </ul>
  <p class="src-line">{e(x['src'])}</p>
</section>
""" for x in extras)
    if g.get("contacts"):
        contacts = "".join(contact_row(*row) for row in g["contacts"])
    else:
        police = "<br>".join(f"{e(p['name'])} {tel(p['tel'])}" for p in g["return_places"] if p.get("tel"))
        contacts = (contact_row("特典の申し込み", ap["office"], ap["tel"])
                    + f"    <div><dt>返納・運転経歴証明書</dt><dd>{police}</dd></div>\n")

    sources = [(s["name"], s["url"], f"ページの日付：{s['date']}") for s in g["sources"]]
    sources += [(hn["name"], hn["url"], "ページの日付：記載なし"),
                (kr["name"], kr["url"], "ページの日付：記載なし"),
                (tk["name"], tk["url"], f"一覧は{tk['as_of']}")]
    source_items = "\n".join(
        f'    <li><a href="{e(u)}" target="_blank" rel="noopener">{e(n)}</a>（{e(dt)}）</li>'
        for n, u, dt in sources)
    line = "https://line.me/R/share?text=" + quote(f"{name}で運転免許を返納したら（じもとくらべ）\n{url}", safe="")
    calc_link = ""
    if ap and ap.get("deadline"):
        calc_link = (f'\n  <p class="calc-link" hidden><a href="#deadline">'
                     f'{e(ap["deadline"]["label"])}から、申し込みの期限を調べる ↓</a></p>')

    main = f"""<nav class="crumbs" aria-label="いまいる場所"><a href="{base or './'}">トップ</a> ＞ <a href="{base}hyogo-menkyo-henno.html">兵庫県の免許返納特典</a> ＞ {e(name)}</nav>
<div class="hero">
  <div class="hero-top">
    <p class="eyebrow">兵庫県・{e(name)}</p>
    <div class="stamp" role="img" aria-label="{jdate(checked)}に確認"><span>確認</span><b>{y}</b><b>{int(m)}.{int(d)}</b></div>
  </div>
  <h1>{e(name)}で運転免許を返納したら</h1>
  <p class="lead">{e(g['lead'])}</p>
</div>

<section class="answer" aria-labelledby="ans-h">
  <h2 id="ans-h">まとめ</h2>
  <dl class="facts">
{"".join(fact(k, v) for k, v in g["facts"])}  </dl>{calc_link}
</section>

<section class="cautions" aria-labelledby="cau-h">
  <h2 id="cau-h">ここだけは気をつけてください</h2>
  <ul>
{lis(g['cautions'], '    ')}
  </ul>
</section>

<section class="steps" aria-labelledby="steps-h">
  <h2 class="section-title" id="steps-h">やることは3つ</h2>
  <ol class="step-list">
    <li class="step" id="step-1">
      <h3><span class="num" aria-hidden="true">1</span>警察で免許を返納する</h3>
      <div class="places">
{places}
      </div>
      <p class="src-line">{e(g['return_note'])}</p>{stations}
      <dl class="facts">
{fact("持っていくもの", "運転免許証（マイナ免許証も持っている人は、両方）")}{fact("手数料", hn['fee'])}{fact("受け取るもの", receive)}      </dl>
      <details class="more">
        <summary>窓口に行けないときは（郵送で返納する）</summary>
        <ul class="bullets">
{lis(hn['mail'], '          ')}
        </ul>
        <p>{ext(hn['url'], '兵庫県警の説明を見る')}</p>
      </details>
      <details class="more">
        <summary>家族が代わりに返納するには</summary>
        <ul class="bullets">
{lis(kr['proxy'], '          ')}
        </ul>
        <p>{ext(kr['proxy_form'], '兵庫県警の書類（PDF）')}</p>
      </details>
    </li>
    <li class="step" id="step-2">
      <h3><span class="num" aria-hidden="true">2</span>{e(step2_title)}</h3>
      <p class="step-lead">{step2_lead}</p>
      <table class="fees">
        <caption>手数料</caption>
        <tbody>
{fees}
        </tbody>
      </table>
      <ul class="bullets">
{lis(kr['points'], '        ')}
      </ul>
    </li>
{step3}
  </ol>
</section>

<section class="checklist" aria-labelledby="chk-h">
  <h2 id="chk-h">持ち物チェック</h2>
  <p class="note">印刷して、チェックしながら使えます。</p>
  <div class="chk-cols">
{chr(10).join(fieldsets)}
  </div>
</section>

<section class="statewide" id="statewide" aria-labelledby="sw-h">
  <h2 id="sw-h">兵庫県内どこでも使える割引</h2>
  <p>{e(tk['who'])}{e(tk['what'])}</p>
  <ul class="bullets">
    <li>{e(tk['bus'])}</li>
{lis(g.get('local_discounts', []), '    ')}
  </ul>
  <ul class="bullets small">
{lis(tk['notes'], '    ')}
  </ul>
  <p>{ext(tk['list_url'], '特典の一覧（PDF）を見る')}</p>
</section>
{extra}
<section class="block contacts" aria-labelledby="ct-h">
  <h2 id="ct-h">問い合わせ先</h2>
  <dl class="facts">
{contacts}  </dl>
</section>

<section class="block share" aria-labelledby="sh-h">
  <h2 id="sh-h">家族に知らせる・紙で持つ</h2>
  <div class="share-row">
    <button type="button" class="btn-act" data-print>印刷する</button>
    <button type="button" class="btn-act" data-copy="{e(url)}">URLをコピー</button>
    <a class="btn-act" href="{e(line)}" target="_blank" rel="noopener">LINEで送る</a>
  </div>
  <p class="note" id="copied" aria-live="polite"></p>
  <input id="copy-url" type="text" readonly value="{e(url)}" hidden aria-label="このページのURL">
</section>

<section class="block sources" aria-labelledby="src-h">
  <h2 id="src-h">確かめたページ</h2>
  <ul class="bullets">
{source_items}
  </ul>
  <p>確かめた日：{jdate(checked)}。制度は変わることがあります。申し込む前に、{unit}のページか窓口で確かめてください。</p>
  <p class="fix">間違いに気づいたら、<a href="{CONTACT_URL}" target="_blank" rel="noopener">お問い合わせフォーム</a>からお知らせください。</p>
</section>
<p class="print-only">{jdate(checked)}に確認（制度は変わることがあります）　{e(url)}</p>
<p class="back"><a href="{base}hyogo-menkyo-henno.html#{c['slug']}">← 兵庫県41市町の一覧にもどる</a></p>"""

    return shell(
        title=f"{g['title']}｜じもとくらべ",
        description=g["description"],
        path=path, main=main, draft=draft, base=base, page_class="guide",
        draft_note=f"{name}の手順ページの試作です。",
        scripts=CITY_SCRIPT + ("\n" + CALC_SCRIPT if calc_link else ""))


# ---------------- トップ ----------------

# トップの「準備中」。TOPICS.md の「これから作る」と同じ順番・名前にそろえる（公開したらここから消す）
UPCOMING = [
    ("補聴器を買うときの助成", "高齢者"),
    ("子どもの医療費の助成", "子育て"),
    ("粗大ごみの出し方と料金", "くらし"),
    ("空き家の補助金", "住まい"),
]


def top_page(data, draft):
    n_benefit = sum(1 for c in data["cities"] if c["k"] in HAS_BENEFIT)
    n_taxi = sum(1 for t in data.get("taxi", {}).values() if t["k"] == "yes")
    taxi_link = ""
    if n_taxi:
        taxi_link = f"""
    <li><a href="{taxi_path(data['pref'])}"><b>高齢者のタクシー代の助成</b>
      <span>{n_taxi}市町で、年齢などで使える助成 ・ {jdate(data['taxi_checked'])}に確認</span></a></li>"""
    guides = [c for c in data["cities"] if c.get("guide")]
    guide_block = ""
    if guides:
        links = "\n".join(
            f'    <li><a href="{GUIDE_DIR}/{c["slug"]}.html"><b>{e(c["n"])}</b>'
            f'<span>{e(c["guide"]["short"])}</span></a></li>' for c in guides)
        guide_block = f"""
<details class="guides">
  <summary><h2 id="gd-h">市町ごとの、返納から申し込みまでの手順（{len(guides)}市町）</h2></summary>
  <p>返納する場所、特典の申し込み方、持ち物を、市町ごとに1ページにまとめています。</p>
  <ul class="guide-links">
{links}
  </ul>
</details>"""
    upcoming = "\n".join(f'    <li><span class="up-tag">{e(tag)}</span>{e(name)}</li>' for name, tag in UPCOMING)
    main = f"""<section class="top-hero">
  <h1 class="name">じもと<span>くらべ</span></h1>
  <p class="lead">住んでいる市や町によって、使える制度はちがいます。市町の公式ページを1つずつ開いて、同じ項目にそろえて並べています。</p>
</section>

<section class="pick top-pick" id="pick" aria-labelledby="pick-h">
  <h2 class="section-title" id="pick-h">あなたの市町を選んでください</h2>
  <p class="pick-lead">兵庫県の41市町。選ぶと、その市町の免許返納の特典と、高齢者のタクシー代の助成が見られます。</p>
  <div class="search">
    <label for="q">名前で探す <span class="hint">（ひらがなでも探せます）</span></label>
    <input id="q" type="search" autocomplete="off" placeholder="例：あかし、丹波">
  </div>
  <div class="pick-list" id="pick-list">
{pick_html(data, "hyogo-menkyo-henno.html")}
  </div>
  <p class="pick-none" id="pick-none" hidden>見つかりませんでした。市や町の名前の一部を、ひらがなで入れてみてください。</p>
</section>

<section class="theme" aria-labelledby="th-car-h">
  <p class="t-eyebrow">兵庫県・41市町</p>
  <h2 id="th-car-h">高齢の家族と、車・移動</h2>
  <ul class="theme-links">
    <li><a href="hyogo-menkyo-henno.html"><b>運転免許を返納したら、何がもらえる？</b>
      <span>{n_benefit}市町で特典や支援 ・ {jdate(data['checked'])}に確認</span></a></li>{taxi_link}
    <li><a href="{HANASHI_PATH}"><b>親に運転の話をはじめる、最初のひと言</b>
      <span>家族が6つの質問に答えると、話しはじめの例が出ます</span></a></li>
  </ul>
</section>

<section class="upcoming" aria-labelledby="up-h">
  <h2 id="up-h">これから比べる制度（準備中）</h2>
  <ul>
{upcoming}
  </ul>
</section>
{guide_block}

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
        path="", main=main, draft=draft, scripts=PICK_SCRIPT)


# ---------------- 最初のひと言（話し方のページ） ----------------

HANASHI_PATH = "henno-hanashikata.html"


def hanashi_page(data, hk, draft):
    """data/hanashikata.json から、親に運転の話をはじめるためのページを作る。
    入力はブラウザの中だけで使い、どこにも送らない（アクセス解析を始めるときは、先にプライバシーポリシーを直す）。"""
    s, m, cs = hk["stats"], hk["manual"], hk["consult"]
    cities = [{
        "slug": c["slug"], "n": c["n"], "y": c["y"], "k": KINDS[c["k"]][0], "has": c["k"] in HAS_BENEFIT,
        "what": c["what"],
        "href": f"{GUIDE_DIR}/{c['slug']}.html" if c.get("guide") else f"hyogo-menkyo-henno.html#{c['slug']}",
    } for c in data["cities"]]
    payload = json.dumps({k: hk[k] for k in ("questions", "types", "triggers", "phrases")} | {"cities": cities},
                         ensure_ascii=False).replace("</", "<\\/")
    n_phr = sum(len(v) for t in hk["phrases"].values() for v in t.values())
    trig_opts = "".join(f'<button type="button" class="hk-chip" data-trig="{k}" aria-pressed="false">{e(v)}</button>'
                        for k, v in hk["triggers"].items())
    city_opts = "".join(f'<option value="{c["slug"]}">{e(c["n"])}</option>' for c in data["cities"])
    ng = "".join(f"<li>{e(x)}</li>" for x in hk["ng"])
    main = f"""<article class="hk">
  <section class="hk-hero">
    <p class="hk-eyebrow">免許返納・家族のための道具</p>
    <h1>親に運転の話をはじめる、<br>最初のひと言</h1>
    <p>家族が6つの質問に答えると、親御さんに合った話しはじめの例が出ます。例は{n_phr}通りあり、何度でも出し直せます。</p>
    <p class="hk-stat"><b>{e(s["year"])}、全国で{e(s["total"])}</b>の運転免許が、本人の申し出で返納されました。1日あたり{e(s["per_day"])}です。そのうち75歳以上が{e(s["over75_rate"])}（{e(s["over75"])}）でした。
      <span class="hk-src">出典：<a href="{e(s["url"])}" target="_blank" rel="noopener">{e(s["src"])}</a>（{jdate(s["checked"])}に確認）</span></p>
    <button type="button" class="hk-btn" data-go="quiz">質問に答える（約1分）</button>
  </section>

  <section class="hk-screen" id="hk-quiz" hidden aria-live="polite">
    <div class="hk-progress" aria-hidden="true"><div id="hk-bar"></div></div>
    <p class="hk-step" id="hk-step"></p>
    <h2 class="hk-q" id="hk-q"></h2>
    <div class="hk-opts" id="hk-opts"></div>
    <button type="button" class="hk-back" id="hk-back">← 前の質問へ</button>
  </section>

  <section class="hk-screen" id="hk-result" hidden>
    <div class="hk-card">
      <h2>運転で気になるサインの多さ</h2>
      <div class="hk-meter" id="hk-meter" aria-hidden="true"><span></span><span></span><span></span></div>
      <p id="hk-risk"></p>
      <p class="hk-note">これは診断ではありません。運転に不安があるときは、本人も家族も<a href="{e(cs["url"])}" target="_blank" rel="noopener">{e(cs["label"])}</a>で警察の相談窓口に相談できます。</p>
    </div>

    <div class="hk-card">
      <p class="hk-type-line">親御さんは <b class="hk-type" id="hk-type"></b></p>
      <p id="hk-type-text"></p>
      <h2>どんな場面で話しますか？</h2>
      <div class="hk-chips" role="group" aria-label="話す場面">{trig_opts}</div>
      <h2>最初のひと言</h2>
      <div id="hk-phrases"></div>
      <p class="hk-more-row"><button type="button" class="hk-more" id="hk-more">別の言い方を見る</button> <span class="hk-count" id="hk-count"></span></p>
      <div class="hk-ng">
        <b>言わないほうがいいこと</b>
        <ul>{ng}</ul>
      </div>
    </div>

    <div class="hk-card">
      <h2>返納したら、住んでいる市町で何がある？</h2>
      <p>兵庫県の41市町は、このサイトで特典を調べています。</p>
      <label class="hk-label" for="hk-city">親御さんの住んでいる市町</label>
      <select id="hk-city" class="hk-select"><option value="">選んでください</option>{city_opts}</select>
      <div id="hk-city-out" class="hk-city-out" hidden></div>
    </div>

    <div class="hk-card">
      <h2>「お金」から話すための計算</h2>
      <p>車をやめると毎月いくら変わるかの目安です。数字があると話しやすくなります。</p>
      <label class="hk-label" for="hk-car">車にかかるお金（保険・ガソリン・税金・車検・駐車場）<b class="hk-val" id="hk-car-v"></b></label>
      <input type="range" id="hk-car" min="10000" max="80000" step="5000" value="35000">
      <label class="hk-label" for="hk-taxi">タクシーを使う回数（1か月）<b class="hk-val" id="hk-taxi-v"></b></label>
      <input type="range" id="hk-taxi" min="0" max="20" step="1" value="6">
      <label class="hk-label" for="hk-net">ネットスーパーや宅配を使う回数（1か月）<b class="hk-val" id="hk-net-v"></b></label>
      <input type="range" id="hk-net" min="0" max="8" step="1" value="2">
      <p class="hk-diff" id="hk-diff"></p>
      <p class="hk-note">タクシー1回2,000円、宅配1回500円として計算した目安です。市町の特典は入れていません。</p>
    </div>

    <div class="hk-card hk-about">
      <h2>このページについて</h2>
      <ul class="bullets small">
        <li>ひと言は、じもとくらべが書いた例です。公的な資料の文章ではありません。</li>
        <li>家族向けのくわしい手引きに、{e(m["by"])}の<a href="{e(m["url"])}" target="_blank" rel="noopener">「{e(m["name"])}」</a>があります。{e(m["scope"])}</li>
      </ul>
    </div>
    <button type="button" class="hk-back" data-go="quiz">もう一度答える</button>
  </section>
</article>"""
    script = """<script id="hk-data" type="application/json">""" + payload + """</script>
<script>
(function () {
  var D = JSON.parse(document.getElementById("hk-data").textContent);
  var $ = function (id) { return document.getElementById(id); };
  var ans = [], i = 0, type = "ready", trig = null;
  var OPTS = [["はい", 2], ["ときどき", 1], ["いいえ", 0]];
  function show(id) {
    ["hk-quiz", "hk-result"].forEach(function (s) { $(s).hidden = s !== id; });
    document.querySelector(".hk-hero").hidden = !!id;
    window.scrollTo(0, 0);
  }
  function start() { ans = []; i = 0; show("hk-quiz"); renderQ(); }
  document.querySelectorAll("[data-go=quiz]").forEach(function (b) { b.addEventListener("click", start); });
  function renderQ() {
    var q = D.questions[i];
    $("hk-bar").style.width = (i / D.questions.length * 100) + "%";
    $("hk-step").textContent = "質問 " + (i + 1) + " / " + D.questions.length;
    $("hk-q").textContent = q.q;
    $("hk-opts").innerHTML = "";
    OPTS.forEach(function (o) {
      var b = document.createElement("button");
      b.type = "button"; b.className = "hk-opt"; b.textContent = o[0];
      b.addEventListener("click", function () {
        ans[i] = o[1];
        if (i < D.questions.length - 1) { i++; renderQ(); } else { result(); }
      });
      $("hk-opts").appendChild(b);
    });
    $("hk-back").style.visibility = i ? "visible" : "hidden";
    $("hk-opts").firstChild.focus();
  }
  $("hk-back").addEventListener("click", function () { if (i) { i--; renderQ(); } });
  function result() {
    var risk = 0, pride = 0, life = 0;
    D.questions.forEach(function (q, k) {
      risk += q.w * ans[k];
      if (q.type === "pride") pride = ans[k];
      if (q.type === "life") life = ans[k];
    });
    var lv = risk >= 9 ? 3 : risk >= 4 ? 2 : 1;
    $("hk-meter").className = "hk-meter lv" + lv;
    $("hk-risk").textContent = ["", "気になるサインは少なめです。", "気になるサインがいくつかあります。早めに話し合いを。", "気になるサインが多めです。できるだけ早く話し合いを。"][lv];
    type = lv === 1 ? "ready" : (pride >= life ? "pride" : "life");
    $("hk-type").textContent = D.types[type].name;
    $("hk-type-text").textContent = D.types[type].text;
    pickTrig(Object.keys(D.triggers)[0]);
    calc();
    show("hk-result");
  }
  var queue = [], qi = 0;
  function shuffle(a) { return a.slice().sort(function () { return Math.random() - .5; }); }
  function buildQueue() {
    var t = D.phrases[type], rest = [];
    Object.keys(t).forEach(function (k) { if (k !== trig) rest = rest.concat(t[k]); });
    queue = shuffle(t[trig]).concat(shuffle(rest)); qi = 0;
  }
  function drawPhrases() {
    if (qi >= queue.length) qi = 0;
    var x = queue[qi++];
    var b = document.createElement("button");
    b.type = "button"; b.className = "hk-phrase";
    b.innerHTML = "<span></span><small>押すとコピーできます</small>";
    b.firstChild.textContent = "「" + x + "」";
    b.addEventListener("click", function () {
      var done = function () { b.classList.add("copied"); b.lastChild.textContent = "コピーしました"; };
      if (navigator.clipboard) navigator.clipboard.writeText(x).then(done, done); else done();
    });
    $("hk-phrases").innerHTML = "";
    $("hk-phrases").appendChild(b);
    $("hk-count").textContent = qi + " / " + queue.length;
  }
  function pickTrig(k) {
    trig = k; buildQueue();
    document.querySelectorAll(".hk-chip").forEach(function (c) { c.setAttribute("aria-pressed", String(c.dataset.trig === k)); });
    drawPhrases();
  }
  document.querySelectorAll(".hk-chip").forEach(function (c) { c.addEventListener("click", function () { pickTrig(c.dataset.trig); }); });
  $("hk-more").addEventListener("click", drawPhrases);
  $("hk-city").addEventListener("change", function () {
    var c = D.cities.filter(function (x) { return x.slug === $("hk-city").value; })[0], o = $("hk-city-out");
    if (!c) { o.hidden = true; return; }
    o.hidden = false;
    o.innerHTML = '<p><b></b> <span class="hk-kind"></span></p><p class="hk-what"></p><a></a>';
    o.querySelector("b").textContent = c.n;
    o.querySelector(".hk-kind").textContent = c.k;
    o.querySelector(".hk-kind").classList.toggle("none", !c.has);
    o.querySelector(".hk-what").textContent = c.what;
    var a = o.querySelector("a"); a.href = c.href; a.textContent = c.n + "のくわしい内容を見る →";
  });
  var yen = function (n) { return Math.abs(n).toLocaleString("ja-JP") + "円"; };
  function calc() {
    var car = +$("hk-car").value, taxi = +$("hk-taxi").value, net = +$("hk-net").value;
    $("hk-car-v").textContent = yen(car);
    $("hk-taxi-v").textContent = taxi + "回";
    $("hk-net-v").textContent = net + "回";
    var d = car - (taxi * 2000 + net * 500);
    $("hk-diff").textContent = d >= 0 ? "毎月 約" + yen(d) + " 浮きます" : "毎月 約" + yen(d) + " 増えます";
    $("hk-diff").classList.toggle("minus", d < 0);
  }
  ["hk-car", "hk-taxi", "hk-net"].forEach(function (id) { $(id).addEventListener("input", calc); });
  // 一覧の市町の欄から来たとき（?city=slug）は、その市町を選んだ状態にしておく
  var from = new URLSearchParams(location.search).get("city");
  if (from && D.cities.some(function (x) { return x.slug === from; })) {
    $("hk-city").value = from;
    $("hk-city").dispatchEvent(new Event("change"));
  }
})();
</script>"""
    return shell(
        title="親に運転の話をはじめる、最初のひと言｜じもとくらべ",
        description=f"親に免許返納の話をどう切り出すか。家族が6つ答えると、親御さんに合った話しはじめの例（{n_phr}通り）と、兵庫県41市町の返納特典が分かります。",
        path=HANASHI_PATH, main=main, draft=draft, scripts=script)


# ---------------- 運営者情報 ----------------

def about_page(draft):
    main = f"""<article class="prose">
  <h1>運営者情報</h1>
  <section aria-label="基本の情報">
    <dl class="info">
      <div><dt>サイト名</dt><dd>じもとくらべ</dd></div>
      <div><dt>アドレス</dt><dd>https://jimotokurabe.jp/</dd></div>
      <div><dt>運営</dt><dd>個人で運営しています</dd></div>
      <div id="contact"><dt>連絡先</dt><dd><a href="{CONTACT_URL}" target="_blank" rel="noopener">お問い合わせフォーム</a>（Googleフォーム）</dd></div>
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
    <p>内容の間違いや、制度が変わったことに気づいたら、<a href="{CONTACT_URL}" target="_blank" rel="noopener">お問い合わせフォーム</a>からお知らせください。確かめて直し、直した日をページに書きます。</p>
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
    main = f"""<article class="prose">
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
    <p>お問い合わせは、<a href="{CONTACT_URL}" target="_blank" rel="noopener">Googleフォーム</a>で受け付けています。送られた内容は、Googleのサーバーに保存されます。</p>
    <p>お問い合わせでいただいた内容やメールアドレスは、お問い合わせへの対応のためだけに使い、ほかの目的には使いません。</p>
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


def load_pref(henno_file):
    """data/<県>-menkyo-henno.json と、あれば data/<県>-taxi.json を読む。"""
    data = json.loads(henno_file.read_text(encoding="utf-8"))
    taxi_file = henno_file.with_name(henno_file.name.replace("-menkyo-henno", "-taxi"))
    if taxi_file.exists():
        taxi = json.loads(taxi_file.read_text(encoding="utf-8"))
        data["taxi_checked"] = taxi["checked"]
        data["taxi"] = {slug: {"checked": taxi["checked"], **t} for slug, t in taxi["cities"].items()}
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT))
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--artifact")
    ap.add_argument("--artifact-main", help="確認用ページで最初に出す市町の slug（省くとトップページ）")
    a = ap.parse_args()
    prefs = [load_pref(f) for f in sorted((ROOT / "data").glob("*-menkyo-henno.json"))]
    data = next(d for d in prefs if d["pref"]["id"] == HOME_PREF)
    others = [d for d in prefs if d is not data]
    hk = json.loads((ROOT / "data" / "hanashikata.json").read_text(encoding="utf-8"))
    data["hk"] = hk
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    guides = [c for c in data["cities"] if c.get("guide")]
    pages = {
        "index.html": top_page(data, a.draft),
        list_path(data["pref"]): list_page(data, a.draft),
        **({taxi_path(data["pref"]): taxi_page(data, a.draft)} if data.get("taxi") else {}),
        **{f"{GUIDE_DIR}/{c['slug']}.html": city_page(c, data, a.draft) for c in guides},
        HANASHI_PATH: hanashi_page(data, hk, a.draft),
        "about.html": about_page(a.draft),
        "privacy.html": privacy_page(a.draft),
    }
    # 下書きの県（pref.draft が true）は、検索に出さず、サイトマップとトップにも載せない
    hidden = set()
    for d in others:
        dr = a.draft or d["pref"].get("draft", False)
        pages[list_path(d["pref"])] = list_page(d, dr)
        if d.get("taxi"):
            pages[taxi_path(d["pref"])] = taxi_page(d, dr)
        if d["pref"].get("draft"):
            hidden |= {list_path(d["pref"]), taxi_path(d["pref"])}
    for name, html in pages.items():
        (out / name).parent.mkdir(parents=True, exist_ok=True)
        (out / name).write_text(html, encoding="utf-8")
    if out.resolve() != ROOT:
        shutil.copy(ROOT / "site.css", out / "site.css")
    if not a.draft:
        urls = ["" if n == "index.html" else n for n in pages if n not in hidden]
        (out / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "".join(f"  <url><loc>{SITE}{u}</loc></url>\n" for u in urls)
            + "</urlset>\n", encoding="utf-8")
        (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}sitemap.xml\n", encoding="utf-8")
    if a.artifact:
        art = Path(a.artifact)
        art.mkdir(parents=True, exist_ok=True)
        if a.artifact_main:
            c = next(c for c in guides if c["slug"] == a.artifact_main)
            first = to_artifact_fragment(city_page(c, data, a.draft, base=""), f"{c['n']}の返納ガイド")
        else:
            first = to_artifact_fragment(pages["index.html"], "じもとくらべ")
        (art / "index.html").write_text(first, encoding="utf-8")
        for name, html in pages.items():
            if name != "index.html":
                (art / name).parent.mkdir(parents=True, exist_ok=True)
                (art / name).write_text(html, encoding="utf-8")
        shutil.copy(ROOT / "site.css", art / "site.css")
    print("built:", ", ".join(pages), "| draft" if a.draft else "")


if __name__ == "__main__":
    main()
