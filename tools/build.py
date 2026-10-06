"""じもとくらべ のページを data/*.json から作る。

  python3 tools/build.py                  # リポジトリ直下に公開用のページを作り直す
  python3 tools/build.py --out /tmp/x --draft --artifact /tmp/y
                                          # 下書き（検索に出さない・下書きの帯を出す）と、確認用ページの形
"""
import argparse
import hashlib
import json
import re
import shutil
from html import escape
from pathlib import Path
from urllib.parse import quote
from bus_pages import bus_page, bus_path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://jimotokurabe.jp/"
CSS_REV = hashlib.sha256((ROOT / "site.css").read_bytes()).hexdigest()[:12]

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
BASIC_GUIDE_PATH = "menkyo-henno-guide.html"
MOBILITY_PATH = "east-harima-mobility.html"
MOBILITY_CITY_DIR = "hyogo-mobility"
MUNICIPAL_MOBILITY_DATA_PATH = "data/municipal-mobility.json"
NATIONAL_MOBILITY_PATH = "mobility.html"
NATIONAL_MOBILITY_DATA_PATH = "mobility-city-index.json"


def mobility_city_path(city_id):
    return f"{MOBILITY_CITY_DIR}/{city_id}.html"


def municipal_mobility_path(pref_id, city_slug):
    return f"{pref_id}-mobility/{city_slug}.html"


def guide_dir(pref):
    return f"{pref['id']}-menkyo-henno"


def list_path(pref):
    return f"{pref['id']}-menkyo-henno.html"


def taxi_path(pref):
    return f"{pref['id']}-taxi.html"


def hk_key(pref, c):
    """最初のひと言のページで市町村を選ぶときの値（兵庫は slug のまま、ほかの県は 県-slug）。"""
    return c["slug"] if pref["id"] == HOME_PREF else f"{pref['id']}-{c['slug']}"


def region_unit(rows):
    """地域の中の数につける単位（23区、5市、8市町村など）。"""
    have = {city_unit(c["n"]) for c in rows}
    return "".join(u for u in "区市町村" if u in have)


def area_word(pref):
    """「県内」「府内」「都内」「道内」。"""
    return pref["name"][-1] + "内"


def city_unit(name):
    return "町" if name.endswith("町") else "村" if name.endswith("村") else "区" if name.endswith("区") else "市"
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


# First measurement cohort: pages selected from the Search Console / GA4 review.
MEASURED_PAGES = {"hyogo-menkyo-henno/kobe.html", "hyogo-menkyo-henno/nishinomiya.html",
                  "saitama-taxi.html", "hyogo-taxi.html", "nagasaki-taxi.html"}
ACTION_SCRIPT = r"""<script>
(function () {
  // Local checks must never send production analytics events.
  if (location.hostname !== "jimotokurabe.jp" && location.hostname !== "www.jimotokurabe.jp") return;
  document.addEventListener("click", function (event) {
    var target = event.target;
    if (!target || !target.closest) return;
    var control = target.closest("a, button");
    if (!control || !control.closest("main") || typeof window.gtag !== "function") return;
    var name = "", params = {page_path: location.pathname};
    if (control.matches("[data-print]")) {
      name = "print_request";
    } else if (control.tagName === "A") {
      var href = control.getAttribute("href") || "";
      if (href.indexOf("tel:") === 0) {
        name = "phone_click";
      } else {
        var url;
        try { url = new URL(href, location.href); } catch (_) { return; }
        if (url.protocol !== "https:" && url.protocol !== "http:") return;
        if (url.hostname === "line.me" && url.pathname.indexOf("/R/share") === 0) {
          name = "share_line";
        } else if (url.origin !== location.origin && /(^|\.)((lg|go)\.jp)$/.test(url.hostname)) {
          name = "official_info_click";
          params.link_domain = url.hostname;
          params.link_path = url.pathname;
        } else if (control.closest("[data-related-support]")) {
          name = "related_support_click";
          params.link_path = url.pathname;
        }
      }
    }
    if (name) window.gtag("event", name, params);
  });
})();
</script>"""


def shell(*, title, description, path, main, draft, draft_note="", scripts="", base="", page_class="", body_class="", styles=""):
    """base は、サイトの直下から見たこのページの位置（下の階層のページなら "../"）。"""
    canonical = SITE + path
    home = base or "./"
    wrap_class = f"wrap {page_class}".strip()
    body_tag = f'<body class="{e(body_class)}">' if body_class else '<body>'
    # 黒背景を全ページに反映するため、全ページでCSSの版を揃える。
    css_href = f"{base}site.css?v={CSS_REV}"
    robots = '<meta name="robots" content="noindex">\n' if draft else ""
    banner = ""
    if draft:
        banner = ('<p class="draft">これは公開前の下書きです。' + draft_note + '</p>')
    return f"""<!doctype html>
<html lang="ja">
<head>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-T1PQ72Q40S"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', 'G-T1PQ72Q40S');
</script>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="google-adsense-account" content="ca-pub-2542211932832864">
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
<link rel="stylesheet" href="{css_href}">{styles}
{SIZE_BOOT}
</head>
{body_tag}
<a class="skip" href="#main">本文へ移動</a>
<div class="{wrap_class}">
<header class="topbar">
  <a class="brand" href="{home}">じもと<span>くらべ</span></a>
  <nav class="site-nav" aria-label="主なメニュー">
    <a href="{base}index.html#search">地域を探す</a>
    <a href="{base}index.html#return">免許返納</a>
    <a href="{base}mobility.html">移動手段</a>
  </nav>
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
{SIZE_SCRIPT}{chr(10) + ACTION_SCRIPT if path in MEASURED_PAGES and not draft else ""}
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
        link += more_source_links(t)
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


def card(c, checked, taxi=None, statewide=True, hk=None, back=None, gdir=GUIDE_DIR, area="県内"):
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
        more = f'<a href="#statewide">{area}どこでも使える割引</a>もあります。' if statewide else ""
        parts.append(f'<p class="note">くわしくは{unit}の窓口で確かめてください。{more}</p>')
    if c.get("flag"):
        parts.append(f'<p class="flag">確かめ方：{e(c["flag"])}</p>')
    if c.get("guide"):
        label = c["guide"].get("link_label", "返納から申し込みまでの手順を見る")
        parts.append(f'<p><a class="btn-guide" href="{gdir}/{c["slug"]}.html">'
                     f'{e(c["n"])}の免許返納｜{e(label)}<span aria-hidden="true">→</span></a></p>')
    if c.get("url"):
        src = c.get("src") or f"{unit}の公式ページ"
        link = (f'<a class="btn-src" href="{e(c["url"])}" target="_blank" rel="noopener">'
                f'{e(src)}を見る<span aria-hidden="true">↗</span></a>')
        dates = f'ページの日付：{e(c["upd"])}<br>確かめた日：{jdate(checked)}'
    else:
        link = f'<span class="empty-src">{unit}の公式ページ：見つかりませんでした</span>'
        dates = f'確かめた日：{jdate(checked)}'
    parts.append(f'<div class="card-foot">\n    {link}\n    <p class="dates">{dates}</p>\n  </div>')
    if hk:
        parts.append(f'<p class="to-hk"><a href="{HANASHI_PATH}?city={hk}">親に話すときの、最初のひと言<span aria-hidden="true"> →</span></a></p>')
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
    if back:
        blocks.append(back)
    body = "\n  ".join(blocks)
    notfound = " is-notfound" if c["k"] == "notfound" else ""
    tk = f' data-taxi="{t["k"]}"' if t else ""
    return f"""<article class="card{notfound}" id="{c['slug']}" data-k="{c['k']}"{tk} aria-labelledby="{c['slug']}-h">
  <div class="card-head">
    <h3 class="city" id="{c['slug']}-h">{e(c['n'])}<span class="yomi">{e(c['y'])}</span></h3>
  </div>
  {body}
</article>"""


# 市町村の欄の下の「もどる」（トップの地図から来た人と、この一覧で探していた人の両方のため）
BACK_LINKS = """<p class="card-back"><a href="#pick">↑ ほかの市町村を選ぶ</a><a href="./">← トップ（地図）にもどる</a></p>"""


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
    var u = count.getAttribute("data-unit") || "市町";
    count.textContent = f === "all" ? cards.length + u + "すべてを表示しています。" : cards.length + u + "のうち " + shown + u + "を表示しています。";
  }
  chips.forEach(function (b) { b.addEventListener("click", function () { apply(b.getAttribute("data-f")); }); });

  // 絞り込み中に市町を選んだときは、その市町が見えるように絞り込みを外す
  document.querySelectorAll(".pick-grid a, .comparison a, a[href='#statewide']").forEach(function (a) {
    a.addEventListener("click", function () {
      var t = document.getElementById(a.getAttribute("href").slice(1));
      if (t && t.closest(".card, .region") && (t.hidden || (t.closest(".region") || {}).hidden)) apply("all");
    });
  });
})();
</script>"""


def pick_html(data, href_prefix="", prefer_guide=False):
    """地域ごとの市町ボタン。href_prefix を付けると、ほかのページの市町の欄へ飛ぶ。"""
    out = []
    for r in data["regions"]:
        rows = [c for c in data["cities"] if c["r"] == r["id"]]
        links = "\n        ".join(
            f'<a href="{guide_dir(data["pref"]) + "/" + c["slug"] + ".html" if prefer_guide and c.get("guide") else href_prefix + "#" + c["slug"]}" '
            f'data-name="{e(c["n"])}" data-yomi="{e(c["y"])}">{e(c["n"])}</a>'
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
      var block = g.closest("[data-pref-block]");
      if (block && block.hidden) { g.hidden = false; return; }
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


def list_page(data, draft, mobility_cities=(), mobility_scopes=None):
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
        cards = "\n".join(card(c, checked, taxi, statewide=bool(sw), hk=hk_key(P, c), back=BACK_LINKS, gdir=guide_dir(P), area=area_word(P)) for c in rows)
        sections.append(f"""<section class="region" id="r-{r['id']}" aria-labelledby="r-{r['id']}-h">
  <div class="region-head">
    <h2 id="r-{r['id']}-h">{e(r['name'])}<span class="rc">{len(rows)}{region_unit(rows)}</span></h2>
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
    if home:
        page_title = f"{pn}の免許返納特典一覧｜{total}{pu}の対象・金額とタクシー助成｜じもとくらべ"
        page_description = (f"{pn}{total}{pu}の免許返納特典を、対象年齢・もらえるもの・金額・申し込み先で比較。"
                            f"ICOCA、タクシー券、バスの無料券などを市町別に確認できます。"
                            f"高齢者のタクシー代の助成も掲載。各市町の公式ページを{jdate(checked)}に確認しました。")
        page_heading = f"{pn}の免許返納特典を{total}{pu}で比較"
        page_lead = (f"{pn}の{total}{pu}について、運転免許を自主返納した人への特典を市町別に掲載。"
                     f"対象年齢、金額、申し込み先を同じ項目で比べられます。"
                     f"返納後の移動に役立つ、高齢者のタクシー代の助成もあわせて確認できます"
                     f"（<a href=\"{taxi_path(P)}\">タクシー代の助成だけの一覧</a>）。")
    else:
        page_title = f"{pn}の免許返納特典{'と高齢者タクシー助成' if taxi else ''} {total}{pu}の一覧（{int(y)}年{int(m)}月確認）｜じもとくらべ"
        page_description = (f"{pn}の{total}{pu}が、運転免許を自主返納した人に出している特典（ICOCA、タクシー券、バスの無料券など）"
                            + ("と、高齢者のタクシー代の助成を、金額・対象の年齢をそろえて" if taxi else "を、金額・対象の年齢・申し込み期限をそろえて")
                            + f"比べられます。{jdate(checked)}に各市町の公式ページで確認。")
        page_heading = "運転免許を返納したら、何がもらえる？"
        page_lead = f"{pn}の{total}{pu}が、運転免許を自主返納した人に出している特典を、同じ項目にそろえて並べました。{taxi_lead}"
    mobility_links = "\n"
    if mobility_cities:
        items = "\n".join(
            f'<li><a href="{mobility_city_path(c["id"])}">{e((mobility_scopes or {}).get(c["id"], c["name"]))}の移動手段・運賃支援を見る</a></li>'
            for c in mobility_cities)
        mobility_links = f'''\n<section class="mobility-entry-list" aria-labelledby="mobility-entry-h">
  <h2 id="mobility-entry-h">地域の移動手段を探す</h2>
  <p>確認済みの地域交通と運賃支援を、市町ごとにまとめました。神戸市西区は一部地区の案内です。</p>
  <ul>{items}</ul>
</section>
'''
    comparison_cities = [c for c in cities if c["k"] in HAS_BENEFIT]
    comparison_html = ""
    if comparison_cities:
        rows = "\n".join(
            f'<li><a href="#{e(c["slug"])}">{e(c["n"])}</a>'
            f'<span data-label="特典・金額">{e(c.get("amt") or c.get("what") or KINDS[c["k"]][0])}</span>'
            f'<span data-label="申込期限">{e(c.get("dl") or "記載なし")}</span></li>'
            for c in comparison_cities[:8])
        comparison_html = f'''\n<section class="comparison" aria-labelledby="comparison-h">
  <h2 id="comparison-h">返納特典を短く比較</h2>
  <p>特典が確認できた{n_benefit}{pu}のうち、地域順の先頭{min(8, n_benefit)}件です。金額の単位や条件は市町村の詳細で確認できます。</p>
  <div class="comparison-head" aria-hidden="true"><span>市区町村</span><span>特典・金額</span><span>申込期限</span></div>
  <ol class="comparison-rows">{rows}</ol>
  <p class="comparison-more"><a href="#pick">町名から探す →</a> <a href="#list-h">すべての特典を見る →</a></p>
</section>'''
    main = f"""<nav class="crumbs" aria-label="いまいる場所"><a href="./">トップ</a> ＞ {pn}の免許返納特典</nav>
<div class="hero">
  <div class="hero-top">
    <p class="eyebrow">{pn}・{total}{pu}</p>
    <div class="stamp" role="img" aria-label="{jdate(checked)}に確認"><span>確認</span><b>{y}</b><b>{int(m)}.{int(d)}</b></div>
  </div>
  <h1>{e(page_heading)}</h1>
  <p class="lead">{page_lead}</p>
  <p class="basic-entry"><a href="{BASIC_GUIDE_PATH}">免許返納の基本ガイド：手続き・運転経歴証明書・返納後の移動を見る →</a></p>
{hk_banner(data.get("hk")) if home else ""}
</div>{comparison_html}{mobility_links}
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
  <p class="count" id="count" aria-live="polite" data-unit="{pu}">{total}{pu}すべてを表示しています。</p>
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
        title=page_title,
        description=page_description,
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
        link += more_source_links(t)
        dates = f'ページの日付：{e(t.get("upd") or "記載なし")}<br>確かめた日：{jdate(t["checked"])}'
    else:
        link = f'<span class="empty-src">{unit}の公式ページ：見つかりませんでした</span>'
        dates = f'確かめた日：{jdate(t["checked"])}'
    parts.append(f'<div class="card-foot">\n    {link}\n    <p class="dates">{dates}</p>\n  </div>')
    parts.append(BACK_LINKS)
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
    <h2 id="r-{r['id']}-h">{e(r['name'])}<span class="rc">{len(rows)}{region_unit(rows)}</span></h2>
    <a href="#pick">{pu}を選び直す ↑</a>
  </div>
{cards}
</section>""")

    legend = "\n".join(
        f'    <div><dt><span class="chip t-{k}">{e(v[0])}</span></dt><dd>{e(v[1])}</dd></div>'
        for k, v in TAXI_KINDS.items() if k != "none")
    flagged = "・".join(c["n"] for c in cities if taxi[c["slug"]].get("flag"))
    related_support = ""
    if P["id"] in {"saitama", "hyogo", "nagasaki"}:
        bus_link = (f'<a href="{bus_path(P)}">{e(pn)}のバス助成・敬老パスを比較する →</a>'
                    if data.get("bus") and not P.get("draft") else "")
        related_support = f"""<section class="answer" data-related-support aria-labelledby="related-support-h">
  <h2 id="related-support-h">タクシー以外の支援も探す</h2>
  <p>免許を返納した人向けの特典と、返納しなくても条件を満たせば使える交通費の助成は、対象が異なります。お住まいの市や町の条件を確認してください。</p>
  <p class="src-links"><a href="{list_path(P)}">{e(pn)}の免許返納特典を探す →</a> {bus_link} <a href="mobility.html">通院・買い物の移動手段を探す →</a></p>
</section>"""
    y, m, d = checked.split("-")
    main = f"""<nav class="crumbs" aria-label="いまいる場所"><a href="./">トップ</a> ＞ {pn}の高齢者のタクシー代の助成</nav>
<div class="hero">
  <div class="hero-top">
    <p class="eyebrow">{pn}・{total}{pu}</p>
    <div class="stamp" role="img" aria-label="{jdate(checked)}に確認"><span>確認</span><b>{y}</b><b>{int(m)}.{int(d)}</b></div>
  </div>
  <h1>高齢者のタクシー代、市や町が助成してくれる？</h1>
  <p class="lead">{pn}の{total}{pu}が、高齢者に出しているタクシー券やタクシー代の助成を、対象の年齢・金額・申し込み先をそろえて並べました。</p>
</div>{chr(10) + related_support if related_support else ""}

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
  <p class="count" id="count" aria-live="polite" data-unit="{pu}">{total}{pu}すべてを表示しています。</p>
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
    """電話番号だけをリンクにし、「（内線…）」などの続きは、ふつうの文字にする。"""
    m = re.match(r"[0-9０-９-]+", num)
    if not m:
        return e(num)
    head, rest = m.group(0), num[m.end():]
    return f'<a class="tel" href="tel:{head.replace("-", "")}">{e(head)}</a>{e(rest)}'


def ext(url, label):
    return (f'<a class="btn-src" href="{e(url)}" target="_blank" rel="noopener">'
            f'{e(label)}<span aria-hidden="true">↗</span></a>')


def more_source_links(t):
    return "".join(ext(s["url"], s["label"] + "を見る") for s in t.get("more_sources", []))


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
    def contact_value(name, phone):
        if phone and phone in name:
            before, _, after = name.partition(phone)
            return f"{e(before)}{tel(phone)}{e(after)}"
        return f"{e(name)} {tel(phone)}" if phone else e(name)

    if isinstance(who, list):
        value = "<br>".join(contact_value(n, t) for n, t in who)
    else:
        value = contact_value(who, number)
    return f"    <div><dt>{e(label)}</dt><dd>{value}</dd></div>\n"


def guide_taxi_mobility(c, t, pref, base):
    """確認済みの一覧データから、手順ページに移動支援を加える。"""
    same = t.get("guide_relation") == "same"
    if t.get("guide_anchor"):
        taxi = f"""  <div class="mobility-panel">
    <h3>{e(t.get('name', 'タクシー代の助成'))}</h3>
    <p>{e(t['guide_relation_note'])}</p>
    <a href="#{e(t['guide_anchor'])}">制度の詳細を見る →</a>
  </div>"""
    elif same:
        relation = (e(t["what"]) if t["k"] in ("henno_only", "notfound")
                    else "上の返納特典と、タクシー代の助成は同じ制度です。")
        henno = (f'<p>{e(t["henno_link"])}</p>'
                 if t.get("henno_link") and t["henno_link"] != "記載なし" and t["k"] != "henno_only" else "")
        taxi = f"""  <div class="mobility-panel">
    <h3>{e(t.get('guide_heading', t.get('name', 'タクシー代の助成')))}</h3>
    <p>{relation}</p>{henno}
    <a href="#ans-h">対象と手順を見る →</a>
  </div>"""
    elif t["k"] in ("yes", "care"):
        facts = "".join((fact("対象", t.get("age")), fact("助成", t.get("amt")),
                         fact("申し込み", t.get("how"))))
        if t.get("henno_link") and t["henno_link"] != "記載なし":
            facts += fact("返納した人は", t["henno_link"])
        relation = (f'    <p>{e(t["guide_relation_note"])}</p>\n'
                    if t.get("guide_relation_note") else "")
        details = (f'    <ul class="bullets">\n{lis(t["guide_details"], "      ")}\n    </ul>\n'
                   if t.get("guide_details") else "")
        taxi = f"""  <div class="mobility-panel">
    <h3>高齢者のタクシー代の助成 <span class="chip t-{t['k']}">{e(TAXI_KINDS[t['k']][0])}</span></h3>
    <p><b>{e(t.get('name', 'タクシー代の助成'))}</b></p>
{relation}    <dl class="facts">
{facts}    </dl>
{details}  </div>"""
    else:
        taxi = f"""  <div class="mobility-panel">
    <h3>{e(t.get('guide_heading', '高齢者のタクシー代の助成'))} <span class="chip t-{t['k']}">{e(TAXI_KINDS[t['k']][0])}</span></h3>
    <p>{e(t['what'])}</p>
  </div>"""
    note = (f'  <p class="mobility-note">{e(t["note"])}</p>\n'
            if t.get("note") and not t.get("guide_relation_note") else "")
    source = ext(t["url"], f"{city_unit(c['n'])}の公式ページを見る") if t.get("url") else ""
    source += more_source_links(t)
    flag = f'  <p class="flag">確かめ方：{e(t["flag"])}</p>\n' if t.get("flag") else ""
    return f"""

<section class="mobility" aria-labelledby="mobility-h">
  <h2 id="mobility-h">返納後の移動に使えるもの</h2>
{taxi}
{note}  <p class="mobility-source">{source} 確かめた日：{jdate(t['checked'])}</p>
{flag}  <p><a href="{base}{HANASHI_PATH}?city={e(hk_key(pref, c))}">親に話すときの、最初のひと言 →</a></p>
</section>"""


def city_page(c, data, draft, base="../"):
    g = c["guide"]
    P = data["pref"]
    pn, pu, pol = P["name"], P["unit"], P["police"]
    cm = data["common"]
    hn, kr, tk = cm["hennou"], cm["keireki"], cm["tokuten"]
    ap = g.get("apply")  # 市町に申し込む特典があるときだけ
    name = c["n"]
    unit = city_unit(name)
    path = f"{guide_dir(P)}/{c['slug']}.html"
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
        <p class="src-line">どの警察署がどの地域を受け持つかは、<a href="{e(hn['stations_url'])}" target="_blank" rel="noopener">{pol}の警察署一覧</a>から、各警察署のページで確かめられます。</p>
      </details>"""

    mail_block = ""
    if hn.get("mail"):
        mail_block = f"""      <details class="more">
        <summary>窓口に行けないときは（郵送で返納する）</summary>
        <ul class="bullets">
{lis(hn['mail'], '          ')}
        </ul>
        <p>{ext(hn['url'], pol + 'の説明を見る')}</p>
      </details>"""

    # 手順2：運転経歴証明書
    step2_title = g.get("step2_title", "運転経歴証明書をつくるか決める")
    if g.get("step2_lead"):
        step2_lead = e(g["step2_lead"])
    else:
        step2_lead = (f"つくらなくても、{e(name)}の特典はもらえます。つくると、65歳以上なら"
                      '<a href="#statewide">' + area_word(P) + 'どこでも使える割引</a>を受けられます。')
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
{fact(ap.get("attach_label", "添えるもの"), ap.get('attach'))}{dup_deadline}{fact(ap.get("address_label", "宛先"), ap.get('address'))}        {contact_row("問い合わせ", ap['office'], ap.get('tel', '')).strip()}
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

    summary_links = ('\n      <p class="src-links">' + " ".join(
        f'<a href="{e(href)}">{e(label)}</a>' for href, label in g.get("summary_links", [])) + '</p>') if g.get("summary_links") else ""

    fieldsets = [f"""    <fieldset>
      <legend>警察へ（手順1・2）</legend>
{checks(cm.get("checklist", POLICE_CHECKLIST))}
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

    mobility = ""
    if g.get("mobility"):
        mobility_items = "\n".join(
            f'    <li><a href="{e(item["href"])}"><b>{e(item["title"])}</b>'
            f'<span>{e(item["summary"])}</span><strong>{e(item["link"])} →</strong></a></li>'
            for item in g["mobility"])
        mobility = f"""

<section class="mobility" aria-labelledby="mobility-h">
  <h2 id="mobility-h">返納後の移動に使えるもの</h2>
  <ul>
{mobility_items}
  </ul>
  <p><a href="{base}{HANASHI_PATH}?city={e(hk_key(P, c))}">親に話すときの、最初のひと言 →</a></p>
</section>"""
    elif c["slug"] in data.get("taxi", {}):
        taxi = data["taxi"][c["slug"]]
        if P["id"] == HOME_PREF or taxi.get("guide_mobility"):
            mobility = guide_taxi_mobility(c, taxi, P, base)

    main = f"""<nav class="crumbs" aria-label="いまいる場所"><a href="{base or './'}">トップ</a> ＞ <a href="{base}{list_path(P)}">{pn}の免許返納特典</a> ＞ {e(name)}</nav>
<div class="hero">
  <div class="hero-top">
    <p class="eyebrow">{pn}・{e(name)}</p>
    <div class="stamp" role="img" aria-label="{jdate(checked)}に確認"><span>確認</span><b>{y}</b><b>{int(m)}.{int(d)}</b></div>
  </div>
  <h1>{e(g.get('heading', f'{name}で運転免許を返納したら'))}</h1>
  <p class="lead">{e(g['lead'])}</p>
</div>

<section class="answer" aria-labelledby="ans-h">
  <h2 id="ans-h">まとめ</h2>
  <dl class="facts">
{"".join(fact(k, v) for k, v in g["facts"])}  </dl>{calc_link}{summary_links}
</section>

<section class="cautions" aria-labelledby="cau-h">
  <h2 id="cau-h">ここだけは気をつけてください</h2>
  <ul>
{lis(g['cautions'], '    ')}
  </ul>
</section>{mobility}

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
{fact("持っていくもの", "運転免許証（マイナ免許証も持っている人は、両方）")}{fact("手数料", hn.get('fee') or "記載なし")}{fact("受け取るもの", receive)}      </dl>
{mail_block}
      <details class="more">
        <summary>家族が代わりに返納するには</summary>
        <ul class="bullets">
{lis(kr['proxy'], '          ')}
        </ul>
{f"        <p>{ext(kr['proxy_form'], pol + 'の書類（PDF）')}</p>" if kr.get('proxy_form') else ""}
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
  <h2 id="sw-h">{pn}内どこでも使える割引</h2>
  <p>{e(tk['who'])}{e(tk['what'])}</p>
  <ul class="bullets">
{lis(([tk['bus']] if tk.get('bus') else []) + g.get('local_discounts', []), '    ')}
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
<p class="back"><a href="{base}{list_path(P)}#{c['slug']}">← {pn}{len(data['cities'])}{pu}の一覧にもどる</a></p>"""

    return shell(
        title=f"{g['title']}｜じもとくらべ",
        description=g["description"],
        path=path, main=main, draft=draft, base=base, page_class="guide",
        draft_note=f"{name}の手順ページの試作です。",
        scripts=CITY_SCRIPT + ("\n" + CALC_SCRIPT if calc_link else ""))


# ---------------- 免許返納の基本ガイド ----------------

def pref_chooser_html(prefs, scope):
    """都道府県を地方別・名前検索で選ぶ共通の入口。リンクは JS 無効時の確認先にもなる。"""
    on = {d["pref"]["id"]: d for d in prefs}
    groups = []
    for region, ids in REGIONS:
        choices = "".join(
            f'<a class="pref-btn" href="{list_path(on[pid]["pref"])}" data-pref-choice="{pid}" '
            f'data-pref-name="{e(on[pid]["pref"]["name"])}"><b>{e(on[pid]["pref"]["name"])}</b>'
            f'<span>{len(on[pid]["cities"])}{e(on[pid]["pref"]["unit"])}</span></a>'
            for pid in ids if pid in on)
        if choices:
            groups.append(f'<div class="pref-region"><h3 class="pr-h">{e(region)}</h3>'
                          f'<div class="pref-btns">{choices}</div></div>')
    return (f'<div class="pref-chooser" data-pref-chooser id="{scope}-pref-chooser">'
            f'<details><summary><span data-pref-current>都道府県を選ぶ</span></summary>'
            f'<div class="pref-chooser-panel"><label for="{scope}-pref-search">都道府県名で探す</label>'
            f'<input id="{scope}-pref-search" type="search" autocomplete="off" placeholder="例：兵庫、大阪">'
            f'<div class="pref-regions">{"".join(groups)}</div>'
            f'<p class="pref-chooser-none" hidden>該当する都道府県がありません。</p>'
            f'</div></details></div>')


PREF_CHOOSER_SCRIPT = """<script>
(function () {
  document.querySelectorAll("[data-pref-chooser]").forEach(function (chooser) {
    var details = chooser.querySelector("details");
    var search = chooser.querySelector("input[type=search]");
    var groups = chooser.querySelectorAll(".pref-region");
    search.addEventListener("input", function () {
      var term = search.value.normalize("NFKC").trim().toLowerCase();
      var total = 0;
      groups.forEach(function (group) {
        var found = 0;
        group.querySelectorAll("[data-pref-choice]").forEach(function (link) {
          var match = !term || link.dataset.prefName.normalize("NFKC").toLowerCase().includes(term);
          link.hidden = !match;
          if (match) found++;
        });
        group.hidden = !found;
        total += found;
      });
      chooser.querySelector(".pref-chooser-none").hidden = !!total;
    });
    chooser.addEventListener("click", function (event) {
      var link = event.target.closest("[data-pref-choice]");
      if (!link || !chooser.contains(link)) return;
      event.preventDefault();
      chooser.querySelector("[data-pref-current]").textContent = link.dataset.prefName;
      details.open = false;
      search.value = "";
      search.dispatchEvent(new Event("input"));
      chooser.dispatchEvent(new CustomEvent("pref:selected", {detail: {id: link.dataset.prefChoice, name: link.dataset.prefName}}));
    });
  });
})();
</script>"""


BASIC_GUIDE_SCRIPT = """<script>
(function () {
  var data = __PREF_DATA__;
  var chooser = document.getElementById("basic-pref-chooser");
  var pref = document.getElementById("basic-pref");
  var city = document.getElementById("basic-city");
  var cityField = document.getElementById("basic-city-field");
  var citySearch = document.getElementById("basic-city-search");
  var cityCount = document.getElementById("basic-city-count");
  var result = document.getElementById("basic-result");
  if (!chooser || !pref || !city || !result) return;
  function option(value, label) { return new Option(label, value); }
  function resetResult() { result.hidden = true; }
  function fillCities() {
    city.replaceChildren(option("", "市町村を選ぶ"));
    var row = data.prefs[pref.value];
    if (!row || !row.cities) { city.disabled = true; return; }
    var term = citySearch.value.normalize("NFKC").toLowerCase().trim();
    var matches = row.cities.filter(function (c) {
      return !term || c.name.normalize("NFKC").toLowerCase().includes(term)
        || c.yomi.normalize("NFKC").toLowerCase().includes(term);
    });
    matches.forEach(function (c) { city.add(option(c.slug, c.name)); });
    city.disabled = !matches.length;
    cityCount.textContent = matches.length ? matches.length + "市町村から選べます" : "見つかりませんでした。市町村名の一部を入力してください。";
  }
  chooser.addEventListener("pref:selected", function (event) {
    pref.value = event.detail.id;
    pref.dispatchEvent(new Event("change"));
  });
  pref.addEventListener("change", function () {
    var row = data.prefs[pref.value];
    cityField.hidden = !row;
    citySearch.value = "";
    resetResult();
    city.replaceChildren(option("", "市町村を選ぶ"));
    city.disabled = true;
    citySearch.disabled = true;
    cityCount.textContent = row ? "市町村を読み込み中…" : "";
    if (!row) return;
    var id = pref.value;
    if (row.cities) { citySearch.disabled = false; fillCities(); return; }
    fetch(row.dataUrl).then(function (response) {
      if (!response.ok) throw new Error("load failed");
      return response.json();
    }).then(function (cities) {
      row.cities = cities;
      if (pref.value !== id) return;
      citySearch.disabled = false;
      fillCities();
    }).catch(function () {
      if (pref.value !== id) return;
      cityCount.replaceChildren("市町村を読み込めませんでした。");
      var fallback = document.createElement("a");
      fallback.href = row.benefit;
      fallback.textContent = row.name + "の一覧から探す →";
      cityCount.append(" ", fallback);
    });
  });
  citySearch.addEventListener("input", function () { fillCities(); resetResult(); });
  city.addEventListener("change", function () {
    var row = data.prefs[pref.value];
    var selected = row && row.cities.find(function (c) { return c.slug === city.value; });
    resetResult();
    if (!selected) return;
    document.getElementById("basic-result-title").textContent = selected.name + "の情報";
    var police = document.getElementById("basic-police-link");
    police.href = row.police;
    police.textContent = row.policeName + "の免許返納手続き（公式） ↗";
    var benefit = document.getElementById("basic-benefit-link");
    benefit.href = selected.benefit;
    benefit.textContent = selected.name + (selected.benefit.includes("#") ? "の免許返納特典を見る →" : "の免許返納の手順と特典を読む →");
    var taxi = document.getElementById("basic-taxi-link");
    taxi.href = selected.taxi;
    taxi.textContent = selected.name + "の高齢者向けタクシー助成を見る →";
    result.hidden = false;
  });
})();
</script>"""


def basic_guide_cities(data):
    """基本ガイドで県を選んだあとだけ読み込む、軽量な市町村データ。"""
    P = data["pref"]
    cities = []
    for c in data["cities"]:
        t = data["taxi"][c["slug"]]
        cities.append({"slug": c["slug"], "name": c["n"], "yomi": c["y"],
                       "kind": KINDS[c["k"]][0], "what": c["what"],
                       "benefit": f'{guide_dir(P)}/{c["slug"]}.html' if c.get("guide") else f'{list_path(P)}#{c["slug"]}',
                       "taxiKind": TAXI_KINDS[t["k"]][0], "taxi": f'{taxi_path(P)}#{c["slug"]}'})
    return cities


def basic_guide_page(prefs, draft):
    """全国共通の説明と、確認済みの47都道府県の手続き・地域情報への入口。"""
    public = [d for d in prefs if not d["pref"].get("draft")]
    procedure_links = json.loads((ROOT / "data" / "henno-procedure-links.json").read_text(encoding="utf-8"))
    links = {}
    for d in public:
        pid = d["pref"]["id"]
        police = d.get("common", {}).get("hennou", {}).get("url") or procedure_links.get(pid, {}).get("url")
        if not police or not d.get("taxi"):
            raise ValueError(f"基本ガイドの確認先が足りません: {pid}")
        links[pid] = {"name": d["pref"]["name"], "policeName": d["pref"]["police"], "police": police,
                      "benefit": list_path(d["pref"]), "count": len(d["cities"]),
                      "dataUrl": f"guide-city-data/{pid}.json"}
    regions = []
    for region, ids in REGIONS:
        rows = [f'<li><a href="{links[pid]["benefit"]}">{e(links[pid]["name"])}の免許返納特典と市町村別の案内</a></li>'
                for pid in ids if pid in links]
        if rows:
            regions.append(f'<div><h3>{e(region)}</h3><ul>{"".join(rows)}</ul></div>')
    payload = json.dumps({"prefs": links}, ensure_ascii=False).replace("</", "<\\/")
    script = PREF_CHOOSER_SCRIPT + BASIC_GUIDE_SCRIPT.replace("__PREF_DATA__", payload)
    main = f"""<article class="basic-guide">
<nav class="crumbs" aria-label="いまいる場所"><a href="./">トップ</a> ＞ 免許返納の基本ガイド</nav>
<header class="basic-hero">
  <p class="basic-kicker">はじめて調べる方へ</p>
  <h1>免許返納の基本ガイド</h1>
  <p class="basic-answer"><strong>運転免許の自主返納は、免許が不要になった人などが本人の意思で申請する手続きです。</strong>返納する場所や必要なものは都道府県警察で確認します。返納後の移動手段と、地域で使える支援も先に調べておくと安心です。</p>
  <nav class="basic-jump" aria-label="このページでわかること"><a href="#before">返納できるか</a><a href="#flow">手続きの流れ</a><a href="#after">返納後の支援</a><a href="#region">市町村の情報を探す</a></nav>
</header>

<section id="before" class="basic-section" aria-labelledby="basic-before-h">
  <p class="basic-kicker">まず確認</p><h2 id="basic-before-h">自主返納できる人・できない人</h2>
  <p>運転しなくなった人や、運転に不安を感じる人は、免許を自主的に返納できます。一方、免許の停止・取消しの行政処分中の人や、その処分の基準に該当する人などは自主返納できません。該当するか迷うときは、手続き前に住所地の都道府県警察へ確認してください。</p>
  <p class="basic-source">出典：<a href="https://www.npa.go.jp/policies/application/license_renewal/jishuhennou.html">警察庁「運転免許証の自主返納について」</a></p>
</section>

<section id="flow" class="basic-section" aria-labelledby="basic-flow-h">
  <p class="basic-kicker">手続きの順序</p><h2 id="basic-flow-h">返納までの3つの確認</h2>
  <ol class="basic-steps">
    <li><span class="basic-num" aria-hidden="true">01</span><div><h3>返納後の移動を考える</h3><p>通院、買い物、家族の送迎など、普段の行き先を書き出します。バス・タクシーや家族の送迎で移動できるかを確かめ、手続き当日の帰り道も決めておきます。返納が完了した後は運転できません。</p></div></li>
    <li><span class="basic-num" aria-hidden="true">02</span><div><h3>住所地の警察に手続きを確認する</h3><p>申請場所、受付時間、必要な書類、代理申請の条件は都道府県警察の案内で確認します。全国共通の窓口や持ち物として決めつけず、下の地域選択から住所地の公式案内へ進んでください。</p></div></li>
    <li><span class="basic-num" aria-hidden="true">03</span><div><h3>運転経歴証明書と地域の支援を確認する</h3><p>運転経歴証明書は、返納した人などが申請できる本人確認用の書類です。返納後5年以上たつと交付を受けられません。地域の特典で提示が必要な場合もあるため、証明書を申請するか警察の案内で確認します。</p></div></li>
  </ol>
  <div class="basic-check"><h3>警察の案内で確認する項目</h3><ul>
    <li>返納できる窓口と受付日・時間</li>
    <li>免許証の種類に応じた持ち物と、代理申請・郵送の条件</li>
    <li>運転経歴証明書を申し込む場合の書類、写真、手数料、受け取り方</li>
  </ul><p>返納の受付方法と証明書の申請方法は別に確認します。費用や必要書類を全国一律と考えず、住所地の案内を見てください。</p></div>
  <p class="basic-source">証明書の対象・期限：<a href="https://www.npa.go.jp/policies/application/license_renewal/jishuhennou.html">警察庁の説明</a>。申請場所など：<a href="https://www.npa.go.jp/link/prefectural.html">各都道府県警察の案内</a>。</p>
</section>

<section id="after" class="basic-section" aria-labelledby="basic-after-h">
  <p class="basic-kicker">返納後の暮らし</p><h2 id="basic-after-h">特典と移動支援は地域で違います</h2>
  <p>返納した人だけを対象にする券・ポイント、運転経歴証明書を見せて使う割引、返納の有無にかかわらず高齢者が使えるタクシー助成があります。対象年齢、住所、申請期限、証明書の要否を市町村ごとに確認してください。</p>
  <p>返納前に、お住まいの市町村の特典と移動手段を確認してください。下の地域選択から、その市町村の情報へ進めます。</p>
</section>

<section class="basic-section" aria-labelledby="basic-faq-h">
  <p class="basic-kicker">よくある疑問</p><h2 id="basic-faq-h">手続きを進める前に</h2>
  <div class="basic-faq"><details><summary>運転経歴証明書は必ず申請しますか？</summary><p>返納とは別に、必要かどうかを考える書類です。返納後の本人確認や地域の割引に使える場合があります。申請方法と手数料は住所地の警察の案内で確認してください。</p></details>
  <details><summary>免許証の有効期限が切れている場合は？</summary><p>警察庁によると、免許を更新せず失効した人も、失効から5年以内なら運転経歴証明書の交付対象です。自主返納の手続きとは状況が異なるため、申請できるかと必要書類を住所地の警察に確認してください。</p></details>
  <details><summary>家族が代わりに返納できますか？</summary><p>代理申請の扱いと必要書類は都道府県警察の案内で確認してください。本人の状況や免許証の種類で条件が変わることがあります。</p></details>
  <details><summary>返納するか、家族でまだ迷っています</summary><p>まずは通院や買い物の移動手段を書き出してみてください。話の切り出し方は、<a href="henno-hanashikata.html">親に運転の話をはじめるためのガイド</a>でも考えられます。</p></details></div>
</section>
<section id="region" class="basic-section basic-destination" aria-labelledby="basic-region-h">
  <p class="basic-kicker">お住まいの情報へ</p><h2 id="basic-region-h">市町村の手順・特典を確認する</h2>
  <p>都道府県と市町村を選ぶと、確認したい地域のページへ進めます。都道府県名が見つからないときは、選択欄の中で名前を入力できます。</p>
  <div class="basic-picker">
    <div class="basic-field"><span class="basic-field-label">都道府県</span>{pref_chooser_html(public, "basic")}<input type="hidden" id="basic-pref"></div>
    <div class="basic-field" id="basic-city-field" hidden><label for="basic-city">市町村</label>
      <div class="basic-city-search"><label for="basic-city-search">市町村名で絞り込む（任意）</label><input id="basic-city-search" type="search" autocomplete="off" placeholder="例：あかし、明石"></div>
      <div class="basic-select"><select id="basic-city" disabled><option value="">市町村を選ぶ</option></select></div><p class="basic-city-count" id="basic-city-count" aria-live="polite"></p>
    </div>
    <div class="basic-result" id="basic-result" hidden aria-live="polite"><h3 id="basic-result-title"></h3>
      <p><a class="basic-result-main" id="basic-benefit-link" href="./">市町村の免許返納特典を見る →</a></p>
      <p class="basic-result-more"><a id="basic-police-link" href="https://www.npa.go.jp/link/prefectural.html" target="_blank" rel="noopener">警察の免許返納手続き（公式）</a><a id="basic-taxi-link" href="./">高齢者向けタクシー助成</a></p>
    </div>
  </div>
  <details class="basic-all"><summary>都道府県別の一覧から探す</summary><div class="basic-regions">{"".join(regions)}</div></details>
  <p class="basic-source">警察の手続きURLは各都道府県警察の案内を確認したものです。市町村の制度は各自治体の原典と確認日を一覧・個別ページに記しています。</p>
</section>
<p class="basic-updated">全国共通の説明は、<time datetime="2026-10-04">2026年10月4日</time>に警察庁のページで確認しました。手続き前に、住所地の都道府県警察で最新情報を確認してください。</p>
</article>"""
    return shell(title="免許返納の基本ガイド｜手続き・運転経歴証明書・返納後の支援｜じもとくらべ",
                 description="免許返納の条件、警察での手続き、運転経歴証明書、返納後の移動支援を順に説明。都道府県警察の公式案内と、市町村別の特典・タクシー助成へ進めます。",
                 path=BASIC_GUIDE_PATH, main=main, draft=draft, page_class="basic-page", scripts=script)


# ---------------- トップ ----------------

# トップの「準備中」。TOPICS.md の「これから作る」と同じ順番・名前にそろえる（公開したらここから消す）
UPCOMING = [
    ("補聴器を買うときの助成", "高齢者"),
    ("子どもの医療費の助成", "子育て"),
    ("粗大ごみの出し方と料金", "くらし"),
    ("空き家の補助金", "住まい"),
]


# トップで県を並べる地方の分け方
REGIONS = [
    ("北海道・東北", ["hokkaido", "aomori", "iwate", "miyagi", "akita", "yamagata", "fukushima"]),
    ("関東", ["ibaraki", "tochigi", "gunma", "saitama", "chiba", "tokyo", "kanagawa"]),
    ("甲信越・北陸", ["niigata", "toyama", "ishikawa", "fukui", "yamanashi", "nagano"]),
    ("東海", ["gifu", "shizuoka", "aichi", "mie"]),
    ("近畿", ["shiga", "kyoto", "osaka", "hyogo", "nara", "wakayama"]),
    ("中国・四国", ["tottori", "shimane", "okayama", "hiroshima", "yamaguchi", "tokushima", "kagawa", "ehime", "kochi"]),
    ("九州・沖縄", ["fukuoka", "saga", "nagasaki", "kumamoto", "oita", "miyazaki", "kagoshima", "okinawa"]),
]


def pref_picker(prefs):
    """トップの「都道府県 → 市町村 → 地域の情報」の入口。"""
    blocks = []
    for d in prefs:
        P = d["pref"]
        blocks.append(f"""  <div class="pref-pick" id="pref-{P['id']}" data-pref-block="{P['id']}">
    <h3 class="pp-h">{e(P['name'])}の{len(d['cities'])}{P['unit']}</h3>
    <p class="pp-links"><a href="{list_path(P)}">免許返納の特典の一覧</a>{f' ・ <a href="{taxi_path(P)}">タクシー代の助成の一覧</a>' if d.get("taxi") else ""}</p>
    <div class="pick-list">
{pick_html(d, list_path(P), prefer_guide=True)}
    </div>
  </div>""")
    return f"""<section class="pick top-pick" id="pick" aria-labelledby="pick-h">
  <h2 class="section-title" id="pick-h">免許返納の特典を市町村で探す</h2>
  <p class="pick-lead">都道府県を選ぶと、市町村の一覧が出ます。市町村名を押すと、特典の有無や内容を確認できます。</p>
  <div class="top-pref-field"><span>都道府県</span>{pref_chooser_html(prefs, "top")}</div>
  <div class="top-city-area" id="top-city-area">
    <p class="top-city-label">市町村を選ぶ</p>
    <div class="search">
      <label for="q">市町村名で絞り込む <span class="hint">（ひらがなでも探せます）</span></label>
      <input id="q" type="search" autocomplete="off" placeholder="例：あかし、さかい">
    </div>
{chr(10).join(blocks)}
    <p class="pick-none" id="pick-none" hidden>見つかりませんでした。市や町の名前の一部を、ひらがなで入れてみてください。</p>
  </div>
</section>"""


PREF_SCRIPT = """<script>
(function () {
  var blocks = document.querySelectorAll("[data-pref-block]");
  if (!blocks.length) return;
  var chooser = document.getElementById("top-pref-chooser");
  var cityArea = document.getElementById("top-city-area");
  var q = document.getElementById("q");
  function show(id) {
    blocks.forEach(function (b) { b.hidden = id ? b.getAttribute("data-pref-block") !== id : false; });
    cityArea.hidden = !id;
    q.value = "";
    q.dispatchEvent(new Event("input"));
    try { if (id) localStorage.setItem("jk-pref", id); } catch (e) {}
  }
  chooser.addEventListener("pref:selected", function (event) { show(event.detail.id); });
  var saved = null;
  try { saved = localStorage.getItem("jk-pref"); } catch (e) {}
  var first = location.hash.replace("#pref-", "") || saved;
  var savedLink = chooser.querySelector('[data-pref-choice="' + first + '"]');
  if (first && savedLink) savedLink.click();
  else show("");
})();
</script>"""


HOME_CITY_SCRIPT = """<script>
(function () {
  var pref = document.getElementById('home-pref');
  var city = document.getElementById('home-city');
  var search = document.getElementById('home-city-search');
  var status = document.getElementById('home-city-status');
  var topicField = document.getElementById('home-topic');
  var paths = document.querySelectorAll('[data-home-topic]');
  var rows = [];
  if (!pref || !city || !search || !status) return;
  function normalize(value) {
    return String(value || '').normalize('NFKC').toLowerCase().replace(/[\\s　]/g, '').replace(/[ァ-ヶ]/g, function (char) {
      return String.fromCharCode(char.charCodeAt(0) - 96);
    });
  }
  function chooseTopic(topic) {
    topicField.value = topic;
    paths.forEach(function (path) {
      path.setAttribute('data-selected', String(path.getAttribute('data-home-topic') === topic));
    });
    document.getElementById('home-topic-label').textContent = topic === 'mobility' ? '移動手段' : topic === 'return' ? '免許返納の特典' : 'タクシー代の助成';
    document.getElementById('home-picker-help').textContent = topic === 'mobility'
      ? '乗れる交通を調べる町を選んでください。' : topic === 'return'
      ? '免許返納の特典を調べる町を選んでください。' : 'タクシー代の助成を調べる町を選んでください。';
  }
  paths.forEach(function (path) {
    path.addEventListener('click', function () { chooseTopic(path.getAttribute('data-home-topic')); });
  });
  function fillCities() {
    var previous = city.value;
    city.replaceChildren(new Option(pref.value ? '市区町村を選ぶ' : '先に都道府県を選ぶ', ''));
    var q = normalize(search.value);
    var matches = rows.filter(function (item) {
      return item.pref === pref.value && (!q || normalize(item.name).includes(q)
        || normalize(item.yomi).includes(q) || normalize(item.slug).includes(q));
    });
    matches.forEach(function (item) { city.add(new Option(item.name, item.slug)); });
    if (matches.some(function (item) { return item.slug === previous; })) city.value = previous;
    city.disabled = !pref.value || !matches.length;
    status.textContent = !pref.value ? '都道府県を選んでください。'
      : matches.length ? matches.length + '市区町村から選べます。' : '見つかりませんでした。市区町村名の一部を入れてください。';
  }
  pref.addEventListener('change', function () {
    search.value = '';
    search.disabled = !pref.value;
    fillCities();
    try { if (pref.value) localStorage.setItem('jk-pref', pref.value); } catch (e) {}
  });
  search.addEventListener('input', fillCities);
  city.addEventListener('change', function () {
    var item = rows.find(function (row) { return row.pref === pref.value && row.slug === city.value; });
    if (!item) return;
    var full = item.details.some(function (d) { return d.level === 'detailed'; });
    var partial = item.details.some(function (d) { return d.level === 'partial'; });
    status.textContent = full || partial ? '確認済みの移動・運賃支援の案内があります。'
      : '交通の詳細は調査中です。確認済みの助成・返納情報は見られます。';
  });
  document.getElementById('home-city-form').addEventListener('submit', function (event) {
    event.preventDefault();
    var item = rows.find(function (row) { return row.pref === pref.value && row.slug === city.value; });
    if (!item) { status.textContent = '市区町村を選んでください。'; city.focus(); return; }
    var detail = item.details.find(function (d) { return d.level === 'detailed'; }) || item.details[0];
    if (topicField.value === 'return') {
      location.href = item.return_url;
    } else if (detail) {
      location.href = detail.url + (topicField.value === 'support' || detail.focus === 'support' ? '#support-h' : '#ride-h');
    } else {
      location.href = 'mobility.html?pref=' + encodeURIComponent(item.pref)
        + '&city=' + encodeURIComponent(item.slug) + '&topic=' + encodeURIComponent(topicField.value);
    }
  });
  window.JK_CITY_DATA = window.JK_CITY_DATA || fetch('mobility-city-index.json?v=dark-20261005').then(function (response) {
    if (!response.ok) throw new Error('load');
    return response.json();
  });
  window.JK_CITY_DATA.then(function (data) {
    rows = data.cities;
    var saved = '';
    try { saved = localStorage.getItem('jk-pref') || ''; } catch (e) {}
    if (saved && pref.querySelector('option[value="' + saved + '"]')) {
      pref.value = saved;
      search.disabled = false;
    }
    fillCities();
  }).catch(function () {
    status.replaceChildren('市区町村の一覧を読み込めませんでした。', ' ');
    var link = document.createElement('a');
    link.href = 'mobility.html';
    link.textContent = '全国の一覧から探す →';
    status.appendChild(link);
  });
})();
</script>"""


HOME_DIRECT_SCRIPT = """<script>
(function () {
  var form = document.getElementById('home-direct-form');
  var query = document.getElementById('home-direct-query');
  var status = document.getElementById('home-direct-status');
  var choices = document.getElementById('home-direct-choices');
  var result = document.getElementById('home-direct-result');
  var links = document.getElementById('home-result-links');
  var rows = [];
  function normalize(value) {
    return String(value || '').normalize('NFKC').toLowerCase().replace(/[\\s　]/g, '').replace(/[ァ-ヶ]/g, function (char) {
      return String.fromCharCode(char.charCodeAt(0) - 96);
    });
  }
  function addCard(title, badge, summary, note, href, linkLabel) {
    var card = document.createElement('article');
    card.className = 'home-result-card';
    var mark = document.createElement('span'); mark.className = 'home-result-badge'; mark.textContent = badge;
    var heading = document.createElement('h3'); heading.textContent = title;
    var body = document.createElement('p'); body.textContent = summary;
    var detail = document.createElement('small'); detail.textContent = note;
    var link = document.createElement('a'); link.href = href; link.textContent = linkLabel + ' →';
    card.append(mark, heading, body, detail, link);
    links.appendChild(card);
  }
  function show(item, scroll) {
    choices.replaceChildren();
    query.value = item.name;
    status.textContent = item.pref_name + item.name + 'の情報を表示しました。地域を変えるには町名を入力してください。';
    document.getElementById('home-result-city').textContent = item.pref_name + ' ' + item.name;
    links.replaceChildren();
    var kinds = {give:'特典あり',discount:'割引あり',elder:'高齢者向け',purchase:'購入補助',end:'終了',none:'なし',notfound:'記載なし'};
    var hasReturn = ['give', 'discount', 'elder', 'purchase'].includes(item.return_kind);
    addCard('免許返納の特典', kinds[item.return_kind] || '調査結果あり',
      hasReturn ? (item.return_amount || '内容と対象を確認できます。') : '市区町村の公式ページで確認した結果を掲載しています。',
      (hasReturn ? (item.return_deadline ? '申請期限：' + item.return_deadline + '。' : '申請期限：記載なし。') : '')
        + (item.return_checked ? ' 確認日：' + item.return_checked : ''),
      item.return_url, hasReturn ? '特典と手順を見る' : '調査結果を見る');
    var taxiKinds = {yes:'助成あり',care:'条件つき',henno_only:'返納者のみ',end:'終了',none:'なし',notfound:'記載なし'};
    addCard('タクシー代の助成', taxiKinds[item.taxi_kind] || '調査中',
      item.taxi_url ? '対象となる年齢や利用条件を確認できます。' : 'この町の助成情報は調査中です。',
      item.taxi_checked ? '確認日：' + item.taxi_checked : '掲載状況をご確認ください。',
      item.taxi_url || 'mobility.html?pref=' + encodeURIComponent(item.pref) + '&city=' + encodeURIComponent(item.slug) + '&topic=support', '助成の情報を見る');
    var full = item.details.some(function (d) { return d.level === 'detailed'; });
    var detail = item.details.find(function (d) { return d.level === 'detailed'; }) || item.details[0];
    addCard('乗れる交通', full ? '詳細案内あり' : detail ? (detail.focus === 'support' ? '運賃支援を確認' : '一部地域を確認') : '詳細は調査中',
      detail ? (detail.focus === 'support' ? '運賃支援の対象範囲を確認できます。交通の詳細は調査中です。' : '対象地区や利用方法を確認できます。')
        : '交通の詳細は調査中です。地域の掲載状況をご案内します。',
      detail ? '対象範囲：' + detail.scope : '地域の掲載状況をご確認ください。',
      detail ? detail.url + (detail.focus === 'support' ? '#support-h' : '#ride-h')
        : 'mobility.html?pref=' + encodeURIComponent(item.pref) + '&city=' + encodeURIComponent(item.slug), '移動手段を見る');
    result.hidden = false;
    var url = new URL(location.href);
    url.searchParams.set('pref', item.pref);
    url.searchParams.set('city', item.slug);
    history.replaceState(null, '', url);
    if (scroll) result.scrollIntoView({behavior:'smooth', block:'start'});
  }
  function update() {
    choices.replaceChildren();
    result.hidden = true;
    var q = normalize(query.value);
    if (!q) { status.textContent = '漢字・ひらがなで全国の市区町村を探せます。同名の町は都道府県で区別します。'; return []; }
    var matches = rows.filter(function (item) {
      return normalize(item.name).includes(q) || normalize(item.yomi).includes(q) || normalize(item.slug).includes(q);
    });
    status.textContent = matches.length ? matches.length + '件見つかりました。候補から町を選んでください。'
      : '見つかりませんでした。ひらがなや市区町村名の一部でお試しください。';
    matches.slice(0, 12).forEach(function (item) {
      var button = document.createElement('button'); button.type = 'button';
      var name = document.createElement('strong'); name.textContent = item.name;
      var area = document.createElement('span'); area.textContent = item.pref_name;
      button.append(name, area);
      button.addEventListener('click', function () { show(item, true); });
      choices.appendChild(button);
    });
    if (matches.length > 12) status.textContent += ' 最初の12件を表示しています。';
    return matches;
  }
  query.addEventListener('input', update);
  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var matches = update();
    if (matches.length === 1) show(matches[0], true);
    else if (matches.length > 1) { status.textContent = '同じ名前の町や候補があります。都道府県を見て選んでください。'; choices.querySelector('button').focus(); }
  });
  window.JK_CITY_DATA = window.JK_CITY_DATA || fetch('mobility-city-index.json?v=dark-20261005').then(function (response) {
    if (!response.ok) throw new Error('load');
    return response.json();
  });
  window.JK_CITY_DATA.then(function (data) {
    rows = data.cities;
    var params = new URLSearchParams(location.search);
    var selected = rows.find(function (item) { return item.pref === params.get('pref') && item.slug === params.get('city'); });
    if (selected) show(selected, false);
    else if (query.value) update();
  }).catch(function () {
    status.replaceChildren('市区町村の一覧を読み込めませんでした。 ', ' ');
    var link = document.createElement('a'); link.href = 'mobility.html'; link.textContent = '全国の一覧から探す →';
    status.appendChild(link);
  });
})();
</script>"""


def top_page(data, draft, others, mobility_index):
    published = [data, *others]
    by_id = {d["pref"]["id"]: d for d in published}
    options = []
    prefecture_groups = []
    for region, ids in PREF_REGIONS:
        group = []
        region_links = []
        for pid in ids.split():
            if pid not in by_id:
                continue
            pref = by_id[pid]["pref"]
            group.append(f'<option value="{e(pid)}">{e(pref["name"])}</option>')
            region_links.append(f'<a href="{e(list_path(pref))}">{e(pref["name"])}</a>')
        if group:
            options.append(f'<optgroup label="{e(region)}">{"".join(group)}</optgroup>')
            prefecture_groups.append(
                f'<details class="home-pref-region"><summary>{e(region)}</summary>'
                f'<nav aria-label="{e(region)}の返納特典">{" ".join(region_links)}</nav></details>')
    city_count = len(mobility_index["cities"])
    detailed_count = sum(bool(row["details"]) for row in mobility_index["cities"])
    detailed_links = "\n".join(
        f'<details><summary>{e(region)}（{sum(len(row["details"]) for row in mobility_index["cities"] if row["pref"] in ids.split())}地域）</summary>'
        f'<nav aria-label="{e(region)}の移動案内">' + " ".join(
            f'<a href="{e(detail["url"])}">{e(detail["scope"])}の移動案内</a>'
            for row in mobility_index["cities"] if row["pref"] in ids.split()
            for detail in row["details"]) + '</nav></details>'
        for region, ids in PREF_REGIONS)
    upcoming = "\n".join(f'    <li><span class="up-tag">{e(tag)}</span>{e(name)}</li>' for name, tag in UPCOMING)
    bus_links = ''.join(f'<li><a href="{bus_path(d["pref"])}"><b>{e(d["pref"]["name"])}の高齢者バス助成・敬老パス</b>'
                        f'<span>対象・料金・使えるバス・申し込みを比べる{"（確認用下書き）" if d["bus"].get("draft") else ""}</span></a></li>'
                        for d in [data, *others] if d.get('bus') and (draft or (not d['bus'].get('draft') and not d['pref'].get('draft'))))
    bus_block = f'\n<section class="theme" aria-labelledby="th-bus-h"><h2 id="th-bus-h">高齢者のバス支援を比べる</h2><ul class="theme-links">{bus_links}</ul></section>' if bus_links else ''
    main = f"""<section class="top-hero">
  <p class="top-hero-kicker">全国の市区町村から</p>
  <h1 class="top-hero-title">お住まいの町で、<br>何が使える？</h1>
  <p class="lead">免許返納の特典、タクシー代の助成、車を使わない移動手段を、町から探せます。</p>
</section>

<section class="home-direct" id="search" aria-labelledby="home-direct-h">
  <h2 id="home-direct-h">市区町村名を入力</h2>
  <form id="home-direct-form" role="search">
    <label class="sr-only" for="home-direct-query">市区町村名</label>
    <div class="home-direct-fields"><input id="home-direct-query" type="search" autocomplete="off" placeholder="例：交野市、かたのし" required><button type="submit">町の情報を見る →</button></div>
  </form>
  <p id="home-direct-status" class="home-direct-status" role="status">漢字・ひらがなで全国の市区町村を探せます。同名の町は都道府県で区別します。</p>
  <div id="home-direct-choices" class="home-direct-choices" aria-label="検索候補"></div>
  <p class="home-direct-alt"><a href="#regions">都道府県別の返納特典を見る ↓</a> <a href="#pick">交通・助成を県から選ぶ ↓</a></p>
</section>

<section id="home-direct-result" class="home-direct-result" aria-live="polite" hidden>
  <p class="home-result-kicker">この町で読める情報</p>
  <h2 id="home-result-city"></h2>
  <div id="home-result-links" class="home-result-links"></div>
  <p class="home-result-note">制度の対象や期限は、各ページにある公式出典で確認してください。</p>
</section>

<h2 class="home-choose-title">何を調べますか？</h2>
<nav class="home-paths" aria-label="調べたい内容を選ぶ">
  <a class="home-path-primary" id="return" href="#pick" data-home-topic="return" data-selected="false">
    <span class="home-path-kicker">返納した人へ</span>
    <strong>免許返納の特典</strong>
    <span>もらえるもの・対象・申請期限</span>
    <b>地域から探す <span aria-hidden="true">↓</span></b>
  </a>
  <a class="home-path-secondary" href="#pick" data-home-topic="support" data-selected="false">
    <span class="home-path-kicker">費用の支援</span>
    <strong>タクシー代の助成</strong>
    <span>返納しなくても使える制度も</span>
    <b>地域から探す <span aria-hidden="true">↓</span></b>
  </a>
  <a class="home-path-secondary" href="#pick" data-home-topic="mobility" data-selected="true">
    <span class="home-path-kicker">移動するために</span>
    <strong>乗れる交通</strong>
    <span>バス・予約交通・タクシー</span>
    <b>地域から探す <span aria-hidden="true">↓</span></b>
  </a>
</nav>

<section class="home-city-picker" id="pick" aria-labelledby="pick-h">
  <div class="home-picker-heading"><div><h2 id="pick-h">お住まいの市区町村を選ぶ</h2><p id="home-picker-help">乗れる交通を調べる町を選んでください。</p></div><span id="home-topic-label">移動手段</span></div>
  <form id="home-city-form" action="{NATIONAL_MOBILITY_PATH}" method="get">
    <input type="hidden" id="home-topic" name="topic" value="mobility">
    <div class="home-city-fields">
      <div><label for="home-pref">都道府県</label><select id="home-pref" name="pref" required><option value="">選んでください</option>{''.join(options)}</select></div>
      <div><label for="home-city-search">市区町村名で絞る <span>任意</span></label><input id="home-city-search" type="search" autocomplete="off" placeholder="例：あかし" disabled></div>
      <div><label for="home-city">市区町村</label><select id="home-city" name="city" required disabled><option value="">先に都道府県を選ぶ</option></select></div>
      <button type="submit">町の情報を見る →</button>
    </div>
  </form>
  <p class="home-city-status" id="home-city-status" role="status">都道府県を選んでください。</p>
  <p class="home-coverage"><span aria-hidden="true">●</span> 全国{city_count:,}市区町村から探せます。移動・支援の個別案内は現在{detailed_count}地域です。</p>
</section>

<section class="home-regions" id="regions" aria-labelledby="home-regions-h">
  <h2 id="home-regions-h">都道府県から返納特典を探す</h2>
  <p>地方を開くと、県別の特典一覧へ進めます。</p>
  <div class="home-region-grid">{''.join(prefecture_groups)}</div>
</section>

<details class="home-featured"><summary>移動手段・運賃支援を確認した{detailed_count}地域を見る</summary><div class="home-featured-groups">{detailed_links}</div></details>

<p class="top-basic-entry"><a href="{BASIC_GUIDE_PATH}"><b>返納の手続きから知りたい方へ</b><span>免許返納の基本ガイドで、条件・警察の手続き・運転経歴証明書を確認する →</span></a></p>{bus_block}

<section class="theme" aria-labelledby="th-car-h">
  <h2 id="th-car-h">家族で読む</h2>
  <ul class="theme-links">
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

<section class="about-list" aria-labelledby="how-h">
  <h2 id="how-h">調べ方</h2>
  <ul class="bullets">
    <li>市町の公式ページを開いて、原文で確かめます。</li>
    <li>確かめた日を、ページごとに書きます。</li>
    <li>ページに書かれていないことは「記載なし」とし、推測で埋めません。</li>
  </ul>
</section>"""
    return shell(
        title="じもとくらべ｜免許返納の特典・タクシー助成・移動手段を町から探す",
        description="お住まいの市区町村から、免許返納の特典、高齢者のタクシー代の助成、乗れる交通を探せます。制度の条件と公式出典も確認できます。",
        path="", main=main, draft=draft, scripts=HOME_CITY_SCRIPT + HOME_DIRECT_SCRIPT,
        page_class="home-page", body_class="wayfinding")


def national_mobility_data(prefs, coverage, regional):
    """既存の市区町村と詳細案内を、全国検索用の共通形式にまとめる。"""
    published = [d for d in prefs if not d["pref"].get("draft")]
    valid_cities = {(d["pref"]["id"], c["slug"])
                    for d in published for c in d["cities"]}
    regional_ids = {c["id"] for c in regional["cities"]}
    details = {}
    for entry in coverage["entries"]:
        key = (entry["pref"], entry["municipality"])
        if key not in valid_cities:
            raise ValueError(f"移動案内の市区町村が存在しません: {key}")
        if entry["page"] == MOBILITY_PATH and entry["city"] not in regional_ids:
            raise ValueError(f"移動案内の詳細IDが存在しません: {entry['city']}")
        if entry["level"] not in {"detailed", "partial"}:
            raise ValueError(f"移動案内の掲載範囲が不正です: {entry['level']}")
        url = (f"{entry['page']}?city={quote(entry['city'])}"
               if entry["page"] == MOBILITY_PATH else entry["page"])
        details.setdefault(key, []).append({
            "scope": entry["scope"],
            "level": entry["level"],
            "url": url,
            "focus": entry.get("focus", "mobility"),
        })
    rows = []
    for d in published:
        pref = d["pref"]
        for c in d["cities"]:
            slug = c["slug"]
            taxi = d.get("taxi", {}).get(slug, {})
            rows.append({
                "key": f"{pref['id']}:{slug}",
                "pref": pref["id"],
                "pref_name": pref["name"],
                "slug": slug,
                "name": c["n"],
                "yomi": c.get("y", ""),
                "taxi_kind": taxi.get("k", ""),
                "taxi_checked": taxi.get("checked", ""),
                "taxi_url": f"{taxi_path(pref)}#{slug}" if taxi else "",
                "return_kind": c["k"],
                "return_amount": c.get("amt", ""),
                "return_deadline": c.get("dl", ""),
                "return_checked": (c.get("guide") or {}).get("checked", d["checked"]),
                "return_url": (f"{guide_dir(pref)}/{slug}.html" if c.get("guide")
                               else f"{list_path(pref)}#{slug}"),
                "details": details.get((pref["id"], slug), []),
            })
    if len(rows) != len({row["key"] for row in rows}):
        raise ValueError("全国移動案内の市区町村キーが重複しています")
    return {"checked": coverage["checked"], "cities": rows}


def national_mobility_page(prefs, coverage, regional, draft):
    by_id = {d["pref"]["id"]: d for d in prefs if not d["pref"].get("draft")}
    options = []
    fallback = []
    for region, ids in PREF_REGIONS:
        region_options = []
        for pid in ids.split():
            if pid not in by_id:
                continue
            pref = by_id[pid]["pref"]
            region_options.append(f'<option value="{e(pid)}">{e(pref["name"])}</option>')
            fallback.append(f'<li><a href="{e(taxi_path(pref))}">{e(pref["name"])}のタクシー助成の調査結果</a></li>')
        options.append(f'<optgroup label="{e(region)}">{"".join(region_options)}</optgroup>')
    regional_hints = {c["id"]: c["hint"] for c in regional["cities"]}
    featured = "\n".join(
        f'<details class="nation-featured-region"><summary>{e(region)}（{sum(1 for entry in coverage["entries"] if entry["pref"] in ids.split() and entry["page"] != MOBILITY_PATH)}地域）</summary>'
        '<div class="nation-featured-grid">' + "\n".join(
            f'<a href="{e(entry["page"])}"><strong>{e(by_id[entry["pref"]]["pref"]["name"])} {e(entry["scope"])}</strong>'
            f'<span>{e(entry.get("hint", regional_hints.get(entry["city"], "移動・支援の確認結果")))}</span></a>'
            for entry in coverage["entries"] if entry["pref"] in ids.split() and entry["page"] != MOBILITY_PATH)
        + '</div></details>'
        for region, ids in PREF_REGIONS)
    main = f"""<nav class="crumbs" aria-label="いまいる場所"><a href="./">トップ</a> ＞ 市区町村の掲載状況</nav>
<header class="nation-intro">
  <p class="mobility-kicker">全国の市区町村から</p>
  <h1>市区町村の掲載状況</h1>
  <p>移動手段や運賃支援を確認した地域と、現在読める助成・返納の情報を案内します。</p>
</header>
<div class="nation-layout">
  <section class="nation-search" aria-labelledby="nation-search-h">
    <h2 id="nation-search-h">お住まいの市区町村</h2>
    <label for="nation-query">市区町村名を入力</label>
    <input type="search" id="nation-query" placeholder="例：明石市、あかしし" autocomplete="off">
    <label for="nation-pref">都道府県で絞る</label>
    <select id="nation-pref"><option value="">全国から探す</option>{''.join(options)}</select>
    <p class="nation-search-help" id="nation-count" role="status">市区町村名を入力するか、都道府県を選んでください。</p>
    <div class="nation-choices" id="nation-choices"></div>
  </section>
  <section class="nation-detail" id="nation-detail" aria-live="polite" hidden>
    <p class="nation-status" id="nation-status"></p>
    <h2 id="nation-city-name"></h2>
    <p class="nation-detail-intro" id="nation-intro"></p>
    <div id="nation-detail-links"></div>
  </section>
</div>
<section class="nation-featured" aria-labelledby="nation-featured-h">
  <h2 id="nation-featured-h">移動手段・運賃支援を確認した地域</h2>
  <p>地域名から、確認した交通や運賃の支援を直接確認できます。</p>
  <div class="nation-featured-regions">{featured}</div>
</section>
<aside class="nation-help"><h2>掲載状況について</h2><p>詳細な交通案内は、地域ごとに確認して追加しています。タクシー助成の「記載なし」は、その地域にバスや予約交通がないという意味ではありません。利用前に公式情報で区域・予約・運行日を確認してください。</p></aside>
<noscript><section class="nation-fallback"><h2>都道府県から助成情報を見る</h2><ul>{''.join(fallback)}</ul></section></noscript>"""
    script = """<script>
(function () {
  var query = document.getElementById('nation-query');
  var pref = document.getElementById('nation-pref');
  var count = document.getElementById('nation-count');
  var choices = document.getElementById('nation-choices');
  var detail = document.getElementById('nation-detail');
  var links = document.getElementById('nation-detail-links');
  var all = [];
  function normalize(value) {
    return String(value || '').normalize('NFKC').toLowerCase().replace(/[\\s　]/g, '').replace(/[ァ-ヶ]/g, function (char) {
      return String.fromCharCode(char.charCodeAt(0) - 96);
    });
  }
  function addLink(box, title, description, url, badge) {
    var card = document.createElement('article');
    card.className = 'nation-link-card';
    if (badge) { var mark = document.createElement('span'); mark.className = 'nation-card-badge'; mark.textContent = badge; card.appendChild(mark); }
    var h = document.createElement('h3'); h.textContent = title; card.appendChild(h);
    var p = document.createElement('p'); p.textContent = description; card.appendChild(p);
    var a = document.createElement('a'); a.href = url; a.textContent = '内容を見る →'; card.appendChild(a);
    box.appendChild(card);
  }
  function show(item, scroll) {
    detail.hidden = false;
    links.replaceChildren();
    document.getElementById('nation-city-name').textContent = item.pref_name + ' ' + item.name;
    var hasFull = item.details.some(function (d) { return d.level === 'detailed'; });
    var hasPartial = item.details.some(function (d) { return d.level === 'partial'; });
    document.getElementById('nation-status').textContent = hasFull || hasPartial ? '確認済みの移動・運賃支援の案内あり' : '交通手段の詳細は調査中';
    document.getElementById('nation-intro').textContent = hasFull || hasPartial ? '確認した交通・運賃支援の候補を、対象範囲とともに案内しています。' : '現在確認できる助成などの調査結果へ進めます。地域のバス・予約交通は順次確認しています。';
    function addMobility() {
      item.details.forEach(function (d) {
        addLink(links, d.scope + 'の移動候補', '確認済みの交通または運賃支援。対象地区や利用条件を確認してください。', d.url + (d.focus === 'support' ? '#support-h' : '#ride-h'), '対象範囲を確認');
      });
    }
    function addSupport() {
      if (item.taxi_url) {
        var kinds = {yes:'助成あり',care:'条件つき',henno_only:'返納者のみ',end:'終了',none:'なし',notfound:'記載なし'};
        var kind = kinds[item.taxi_kind] || '調査結果';
        addLink(links, '高齢者のタクシー代の助成', '調査結果：' + kind + '。' + (item.taxi_checked ? '確認日：' + item.taxi_checked + '。' : '') + '対象条件と出典を確認できます。', item.taxi_url, '助成の調査結果');
      }
      addLink(links, '免許返納の特典', '市区町村の特典と申請条件の調査結果を確認できます。', item.return_url, '返納の情報');
    }
    if (new URLSearchParams(location.search).get('topic') === 'support') { addSupport(); addMobility(); }
    else { addMobility(); addSupport(); }
    var url = new URL(location.href);
    url.searchParams.set('pref', item.pref);
    url.searchParams.set('city', item.slug);
    history.replaceState(null, '', url);
    if (scroll) detail.scrollIntoView({behavior:'smooth', block:'start'});
  }
  function update() {
    choices.replaceChildren();
    detail.hidden = true;
    var q = normalize(query.value);
    var pid = pref.value;
    if (!q && !pid) { count.textContent = '市区町村名を入力するか、都道府県を選んでください。'; return; }
    var matches = all.filter(function (item) {
      return (!pid || item.pref === pid) && (!q || normalize(item.name).includes(q) || normalize(item.yomi).includes(q) || normalize(item.slug).includes(q));
    });
    count.textContent = matches.length ? matches.length + '件見つかりました。' + (matches.length > 20 ? '最初の20件を表示中。市区町村名を入力すると絞れます。' : '') : '該当する市区町村が見つかりません。県名や表記を変えてお試しください。';
    matches.slice(0, 20).forEach(function (item) {
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'nation-choice';
      var name = document.createElement('strong'); name.textContent = item.name;
      var area = document.createElement('span'); area.textContent = item.pref_name;
      button.append(name, area);
      button.addEventListener('click', function () { show(item, true); });
      choices.appendChild(button);
    });
  }
  query.addEventListener('input', update);
  pref.addEventListener('change', update);
  query.addEventListener('keydown', function (event) {
    if (event.key === 'Enter') { var first = choices.querySelector('button'); if (first) { event.preventDefault(); first.click(); } }
  });
  fetch('mobility-city-index.json').then(function (response) {
    if (!response.ok) throw new Error('load');
    return response.json();
  }).then(function (data) {
    all = data.cities;
    var params = new URLSearchParams(location.search);
    var selected = all.find(function (item) { return item.pref === params.get('pref') && item.slug === params.get('city'); });
    if (selected) { pref.value = selected.pref; query.value = selected.name; update(); show(selected, false); detail.scrollIntoView({block:'start'}); }
    else update();
  }).catch(function () { count.textContent = '市区町村の一覧を読み込めませんでした。ページを再読み込みしてください。'; });
})();
</script>"""
    return shell(title="全国の移動手段を市区町村から探す｜じもとくらべ",
                 description="全国の市区町村から、地域交通の詳細案内と高齢者のタクシー助成・免許返納の調査結果を探せます。",
                 path=NATIONAL_MOBILITY_PATH, main=main, draft=draft,
                 page_class="mobility-national-page", body_class="wayfinding", scripts=script)


def mobility_card(item, heading="h4", item_id=""):
    tags = "".join(f'<span class="mobility-tag">{e(tag)}</span>' for tag in item["tags"])
    purposes = " ".join(item["purposes"])
    identifier = f' id="{e(item_id)}"' if item_id else ""
    facts = "".join(
        f'<div><dt>{label}</dt><dd>{e(item[key])}</dd></div>'
        for key, label in (("service_area", "使える地域"), ("eligibility", "対象"),
                           ("booking", "予約・申込"), ("fare", "費用"),
                           ("operating_days", "運行日")) if item.get(key))
    fact_list = f'<dl class="mobility-card-facts">{facts}</dl>\n  ' if facts else ""
    return f"""<article class="mobility-card"{identifier} data-purposes="{purposes}">
  <div class="mobility-tags">{tags}</div>
  <{heading}>{e(item['name'])}</{heading}>
  <p>{e(item['summary'])}</p>
  {fact_list}<div class="mobility-check"><b>使う前に確認</b><span>{e(item['check'])}</span></div>
  <a href="{e(item['source'])}" target="_blank" rel="noopener">公式ページで詳細を見る <span aria-hidden="true">↗</span></a>
</article>"""


def mobility_page(data, draft, mobility_scopes=None):
    cities = data["cities"]
    groups = data["groups"]
    group_choices = "\n".join(
        f'<button type="button" data-area-choice="{e(g["id"])}"'
        f' aria-pressed="{"true" if i == 0 else "false"}"><b>{e(g["name"])}</b><small>{e(g["hint"])}</small></button>'
        for i, g in enumerate(groups))
    choices = "\n".join(
        f'<button type="button" class="mobility-choice" data-city-choice="{e(c["id"])}"'
        f' data-city-group="{e(c["group"])}"{" hidden" if c["group"] != groups[0]["id"] else ""}'
        f' aria-pressed="{"true" if i == 0 else "false"}"><b>{e(c["name"])}</b><small>{e(c["hint"])}</small></button>'
        for i, c in enumerate(cities))
    results = "\n".join(f"""<section class="mobility-city" data-mobility-city="{e(c['id'])}"{' hidden' if i else ''}>
  <div class="mobility-result-head"><p class="mobility-kicker">選んだ地域</p><h2>{e(c['name'])}の移動候補</h2>
  <p>住所や停留所を入力していないため、利用できるかどうかは各公式ページで確認してください。</p>
  <a href="{mobility_city_path(c['id'])}">{e((mobility_scopes or {}).get(c['id'], c['name']))}の情報を1ページで読む →</a></div>
  <section class="mobility-group"><h3><span>01</span> 実際に乗る交通手段</h3><div class="mobility-cards">{''.join(mobility_card(x) for x in c['rides'])}</div></section>
  <section class="mobility-group"><h3><span>02</span> 運賃の割引・助成</h3><div class="mobility-cards">{''.join(mobility_card(x) for x in c['supports'])}</div></section>
</section>""" for i, c in enumerate(cities))
    city_links = "\n".join(
        f'<a href="{mobility_city_path(c["id"])}">{e((mobility_scopes or {}).get(c["id"], c["name"]))}の移動手段を見る</a>'
        for c in cities)
    main = f"""<nav class="crumbs" aria-label="いまいる場所"><a href="./">トップ</a> ＞ 東播磨と周辺の移動手段</nav>
<section class="mobility-hero">
  <p class="mobility-kicker">東播磨と周辺の移動案内 / {jdate(data['checked'])}確認</p>
  <h1>車を使わず、<br><em>どう行く？</em></h1>
  <p>買い物や通院に使える地域の交通を、住む市区町から探せます。バス・予約交通と、運賃の助成を分けて案内します。</p>
  <div class="mobility-hero-route" aria-hidden="true"><i></i><i></i><i></i><span>住む地域</span><span>外出の目的</span><span>移動候補</span></div>
</section>
<div class="mobility-layout">
  <form class="mobility-form" id="mobility-form">
    <fieldset><legend><span class="mobility-step">1</span> お住まいはどこですか？</legend>
      <p class="mobility-field-help">地域を選んでから、市区町を選んでください。</p>
      <div class="mobility-areas" role="group" aria-label="地域">{group_choices}</div>
      <div class="mobility-choices">{choices}</div>
    </fieldset>
    <fieldset><legend><span class="mobility-step">2</span> どんな外出ですか？</legend>
      <p class="mobility-field-help">目的に合う交通を優先して表示します。</p>
      <div class="mobility-purpose">
        <button type="button" data-purpose="shopping" aria-pressed="true">買い物</button>
        <button type="button" data-purpose="hospital" aria-pressed="false">通院</button>
        <button type="button" data-purpose="other" aria-pressed="false">その他</button>
      </div>
    </fieldset>
  </form>
  <div class="mobility-results" id="mobility-results" aria-live="polite" aria-atomic="false">{results}</div>
</div>
<nav class="mobility-city-links" aria-label="地域別の移動案内">
  <h2>地域別に読む</h2><div>{city_links}</div>
</nav>
<aside class="mobility-note"><h2>この画面で分かること</h2><p>地域で使える可能性がある交通手段と助成の入口です。利用条件は年齢、居住日、地区、介護認定、予約、目的地などで変わります。運行時刻と停留所は公式ページで直前に確認してください。</p></aside>"""
    script = """<script>
(function () {
  var form = document.getElementById('mobility-form');
  var sections = document.querySelectorAll('[data-mobility-city]');
  if (!form || !sections.length) return;
  var params = new URLSearchParams(location.search);
  var city = form.querySelector('[data-city-choice="' + params.get('city') + '"]');
  var purpose = form.querySelector('[data-purpose="' + params.get('purpose') + '"]');
  var selectedCity = city ? city.getAttribute('data-city-choice') : 'akashi';
  var selectedArea = city ? city.getAttribute('data-city-group') : 'core';
  var selectedPurpose = purpose ? purpose.getAttribute('data-purpose') : 'shopping';
  function update() {
    form.querySelectorAll('[data-area-choice]').forEach(function (button) {
      button.setAttribute('aria-pressed', String(button.getAttribute('data-area-choice') === selectedArea));
    });
    form.querySelectorAll('[data-city-choice]').forEach(function (button) {
      button.hidden = button.getAttribute('data-city-group') !== selectedArea;
      button.setAttribute('aria-pressed', String(button.getAttribute('data-city-choice') === selectedCity));
    });
    form.querySelectorAll('[data-purpose]').forEach(function (button) {
      button.setAttribute('aria-pressed', String(button.getAttribute('data-purpose') === selectedPurpose));
    });
    sections.forEach(function (section) {
      section.hidden = section.getAttribute('data-mobility-city') !== selectedCity;
      section.querySelectorAll('[data-purposes]').forEach(function (card) {
        card.hidden = card.getAttribute('data-purposes').split(' ').indexOf(selectedPurpose) < 0;
      });
    });
    var next = new URL(location.href);
    next.searchParams.set('city', selectedCity);
    next.searchParams.set('purpose', selectedPurpose);
    history.replaceState(null, '', next);
  }
  form.querySelectorAll('[data-area-choice]').forEach(function (button) {
    button.addEventListener('click', function () {
      selectedArea = button.getAttribute('data-area-choice');
      selectedCity = form.querySelector('[data-city-group="' + selectedArea + '"]').getAttribute('data-city-choice');
      update();
    });
  });
  form.querySelectorAll('[data-city-choice]').forEach(function (button) {
    button.addEventListener('click', function () { selectedCity = button.getAttribute('data-city-choice'); selectedArea = button.getAttribute('data-city-group'); update(); });
  });
  form.querySelectorAll('[data-purpose]').forEach(function (button) {
    button.addEventListener('click', function () { selectedPurpose = button.getAttribute('data-purpose'); update(); });
  });
  update();
})();
</script>"""
    return shell(title="東播磨と周辺の移動手段を探す｜じもとくらべ",
                 description="東播磨と周辺地域の交通手段と運賃助成を、住む市区町と外出目的から探せます。",
                 path=MOBILITY_PATH, main=main, draft=draft, page_class="mobility-page", scripts=script)


def mobility_city_page(city, coverage, pref_data, regional_cities, mobility_scopes, checked, draft, regional=True):
    """地域交通の確認済みデータから、検索で直接開ける地域別ページを作る。"""
    name = city["name"]
    scope = coverage["scope"]
    path = coverage["page"]
    partial = coverage["level"] == "partial"
    guide_city = next(c for c in pref_data["cities"] if c["slug"] == coverage["municipality"])
    guide = (f'{guide_dir(pref_data["pref"])}/{guide_city["slug"]}.html'
             if guide_city.get("guide") else f'{list_path(pref_data["pref"])}#{guide_city["slug"]}')
    return_checked = guide_city.get("guide", {}).get("checked", pref_data["checked"])
    return_summary = guide_city.get("what") or "免許返納の特典・申請条件の調査結果を確認できます。"
    ride_links = "".join(f'<a href="#ride-{i}">{e(item["name"])}</a>'
                         for i, item in enumerate(city["rides"], 1))
    support_links = "".join(f'<a href="#support-{i}">{e(item["name"])}</a>'
                            for i, item in enumerate(city["supports"], 1))
    if not ride_links:
        ride_links = "このページでは個別の交通手段を未掲載。運賃の支援をご確認ください。"
    if not support_links:
        support_links = "確認した範囲では未掲載。既存の助成調査もご覧ください。"
    rides = "\n".join(mobility_card(item, "h3", f"ride-{i}")
                      for i, item in enumerate(city["rides"], 1))
    supports = "\n".join(mobility_card(item, "h3", f"support-{i}")
                         for i, item in enumerate(city["supports"], 1))
    other_cities = "\n".join(
        f'<a href="{e(other["id"])}.html">{e(mobility_scopes[other["id"]])}の移動手段</a>'
        for other in regional_cities if other["id"] != city["id"])
    other_nav = (f'<nav class="mobility-city-nearby" aria-label="ほかの地域の移動案内"><h2>ほかの地域を見る</h2><div>{other_cities}</div></nav>'
                 if other_cities else "")
    purpose_link = (f'<a href="../east-harima-mobility.html?city={e(city["id"])}">外出目的で交通候補を絞る →</a>\n  '
                    if regional else "")
    support_note = ("" if city["supports"] else
                    f'<p>個別の運賃助成はこのページでは掲載していません。<a href="../{e(taxi_path(pref_data["pref"]))}#{e(guide_city["slug"])}">既存のタクシー助成の調査結果</a>もご確認ください。</p>')
    ride_note = ("" if city["rides"] else
                 '<p>このページでは個別の交通手段を掲載していません。以下の運賃支援と公式案内をご確認ください。</p>')
    scope_note = (f'{scope}で確認した移動・支援の候補です。この地域の全交通手段を網羅した案内ではありません。'
                  if partial else '住む地区と目的地で使える交通が変わります。')
    main = f'''<nav class="crumbs" aria-label="いまいる場所"><a href="../">トップ</a> ＞ <a href="../mobility.html">移動手段を探す</a> ＞ {e(scope)}</nav>
<header class="mobility-city-hero">
  <p class="mobility-kicker">{e(pref_data['pref']['name'])}の移動案内</p>
  <h1>{e(scope)}の移動案内</h1>
  <p>{e(scope_note)}</p>
</header>
<nav class="mobility-city-sections" aria-label="この地域で調べる内容">
  <a href="#ride-h">移動手段</a><a href="#support-h">運賃の助成</a><a href="#return-h">免許返納</a>
</nav>
<section class="mobility-city-overview" aria-labelledby="overview-h">
  <div class="mobility-city-overview-heading">
    <h2 id="overview-h">この地域で確認した候補</h2>
    <p>公式確認 <time datetime="{e(checked)}">{jdate(checked)}</time></p>
  </div>
  <dl class="mobility-city-summary">
    <div><dt>交通</dt><dd>{ride_links}</dd></div>
    <div><dt>割引・助成</dt><dd>{support_links}</dd></div>
    <div><dt>対象・範囲</dt><dd>{e(city['quick_scope'])}</dd></div>
  </dl>
  <p>対象地区・運行日・予約などは、利用前に公式ページで確かめてください。</p>
</section>
<div class="mobility-city-content">
  <section class="mobility-group" aria-labelledby="ride-h"><h2 id="ride-h">実際に乗る交通手段</h2>{ride_note}<div class="mobility-cards">{rides}</div></section>
  <section class="mobility-group" aria-labelledby="support-h"><h2 id="support-h">運賃の割引・助成</h2>{support_note}<div class="mobility-cards">{supports}</div></section>
</div>
<section class="mobility-city-return" aria-labelledby="return-h">
  <h2 id="return-h">{e(guide_city['n'])}の免許返納</h2>
  <p>{e(return_summary)}</p>
  <a href="../{e(guide)}">対象・申請方法と公式出典を見る →</a>
  <p class="mobility-city-return-date">返納情報を確認した日：<time datetime="{e(return_checked)}">{jdate(return_checked)}</time></p>
</section>
<section class="mobility-city-next" aria-labelledby="next-h">
  <h2 id="next-h">続けて確認する</h2>
  {purpose_link}<a href="../{e(guide)}">{e(guide_city['n'])}の免許返納の情報 →</a>
  <a href="../{e(taxi_path(pref_data['pref']))}#{e(guide_city['slug'])}">{e(guide_city['n'])}のタクシー助成の調査結果 →</a>
</section>
{other_nav}
<p class="mobility-city-updated">公式ページを確認した日：{jdate(checked)}。運行内容や制度は変わるため、利用前に各公式ページで最新情報を確認してください。</p>'''
    description = (f'{scope}の移動手段と運賃支援。{city["quick_scope"]}'
                   f'公式ページを{jdate(checked)}に確認。')
    return shell(title=f'{city["search_title"]}｜じもとくらべ',
                 description=description, path=path, main=main, draft=draft,
                 base='../', page_class='mobility-city-page', body_class='wayfinding')


# ---------------- 最初のひと言（話し方のページ） ----------------

HANASHI_PATH = "henno-hanashikata.html"
PREF_REGIONS = [
    ("北海道・東北", "hokkaido aomori iwate miyagi akita yamagata fukushima"),
    ("関東", "ibaraki tochigi gunma saitama chiba tokyo kanagawa"),
    ("甲信越・北陸", "niigata toyama ishikawa fukui yamanashi nagano"),
    ("東海", "gifu shizuoka aichi mie"),
    ("近畿", "shiga kyoto osaka hyogo nara wakayama"),
    ("中国", "tottori shimane okayama hiroshima yamaguchi"),
    ("四国", "tokushima kagawa ehime kochi"),
    ("九州・沖縄", "fukuoka saga nagasaki kumamoto oita miyazaki kagoshima okinawa"),
]


def hanashi_page(data, hk, draft, prefs=None):
    """data/hanashikata.json から、親に運転の話をはじめるためのページを作る。
    質問への入力内容はブラウザの中だけで使い、サイトには送らない。"""
    s, m, cs = hk["stats"], hk["manual"], hk["consult"]
    prefs = prefs or [data]
    police_links = json.loads((ROOT / "data" / "henno-procedure-links.json").read_text(encoding="utf-8"))
    def procedure_url(d):
        return d.get("common", {}).get("hennou", {}).get("url") or police_links.get(d["pref"]["id"], {}).get("url", "")
    if any(not procedure_url(d) for d in prefs):
        missing = [d["pref"]["id"] for d in prefs if not procedure_url(d)]
        raise ValueError(f"免許返納の公式手続きURLがありません: {', '.join(missing)}")
    missing_taxi = [f"{d['pref']['id']}/{c['slug']}" for d in prefs for c in d["cities"]
                    if c["slug"] not in d.get("taxi", {})]
    if missing_taxi:
        raise ValueError(f"タクシー助成データがありません: {', '.join(missing_taxi)}")
    cities = [{
        "slug": hk_key(d["pref"], c), "pref": d["pref"]["id"], "n": c["n"], "y": c["y"], "k": KINDS[c["k"]][0], "has": c["k"] in HAS_BENEFIT,
        "what": c["what"],
        "benefitHref": f"{guide_dir(d['pref'])}/{c['slug']}.html" if c.get("guide") else f"{list_path(d['pref'])}#{c['slug']}",
        "taxiKind": TAXI_KINDS[d["taxi"][c["slug"]]["k"]][0],
        "taxiHref": f"{taxi_path(d['pref'])}#{c['slug']}",
        "procedureKind": "市町村の手順" if c.get("guide") else ("警視庁の案内" if d["pref"]["id"] == "tokyo" else f"{d['pref']['name']}警の案内"),
        "procedureHref": f"{guide_dir(d['pref'])}/{c['slug']}.html" if c.get("guide") else procedure_url(d),
        "procedureExternal": not bool(c.get("guide")),
    } for d in prefs for c in d["cities"]]
    pref_names = {d["pref"]["id"]: d["pref"]["name"] for d in prefs}
    payload = json.dumps({k: hk[k] for k in ("questions", "types", "triggers", "phrases")} | {"cities": cities, "prefNames": pref_names},
                         ensure_ascii=False).replace("</", "<\\/")
    trig_opts = "".join(f'<button type="button" class="hk-chip" data-trig="{k}" aria-pressed="false">{e(v)}</button>'
                        for k, v in hk["triggers"].items())
    region_html = "".join(
        f'<details class="hk-region"><summary>{e(region)}</summary><div class="hk-pref-grid">'
        + "".join(f'<button type="button" data-pref-id="{pid}" aria-pressed="false">{e(pref_names[pid])}</button>'
                  for pid in ids.split() if pid in pref_names)
        + "</div></details>"
        for region, ids in PREF_REGIONS if any(pid in pref_names for pid in ids.split()))
    def pref_picker(suffix):
        return (f'<div class="hk-pref-picker"><p class="hk-label" id="hk-pref-label-{suffix}">親御さんの住んでいる都道府県</p>'
                f'<details class="hk-pref-details"><summary aria-labelledby="hk-pref-label-{suffix} hk-pref-choice-{suffix}">'
                f'<span class="hk-pref-choice" id="hk-pref-choice-{suffix}">都道府県を選ぶ</span></summary>'
                f'<div class="hk-region-list">{region_html}</div></details></div>')
    n_all = sum(len(d["cities"]) for d in prefs)
    ng = "".join(f"<li>{e(x)}</li>" for x in hk["ng"])
    main = f"""<article class="hk">
  <section class="hk-hero">
    <p class="hk-eyebrow">免許返納・家族のための道具</p>
    <h1>親に免許返納をどう切り出す？<br>最初のひと言を考える</h1>
    <p>親の運転が心配でも、免許返納の話をどう始めればいいか迷うもの。6つの質問に答えると、親御さんの様子に合わせた話しはじめの例を見られます。返納後の移動に役立つ、お住まいの市町村の特典も調べられます。</p>
    {pref_picker("start")}
    <p class="hk-note">都道府県は返納特典を探すために使います。ひと言の例は地域で変わりません。</p>
    <button type="button" class="hk-btn" data-go="quiz">最初のひと言を見つける（約1分）</button>
    <p class="hk-stat"><b>{e(s["year"])}、全国で{e(s["total"])}</b>の運転免許が、本人の申し出で返納されました。1日あたり{e(s["per_day"])}です。そのうち75歳以上が{e(s["over75_rate"])}（{e(s["over75"])}）でした。
      <span class="hk-src">出典：<a href="{e(s["url"])}" target="_blank" rel="noopener">{e(s["src"])}</a>（{jdate(s["checked"])}に確認）</span></p>
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
      <h2>親御さんの市町村で、次に確認すること</h2>
      <p>全国{len(prefs)}都道府県の{n_all}市町村について、返納特典と移動の支援を調べています。</p>
      {pref_picker("result")}
      <label class="hk-label" for="hk-city">親御さんの住んでいる市町村</label>
      <select id="hk-city" class="hk-select" disabled><option value="">先に都道府県を選んでください</option></select>
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
  var ans = [], i = 0, type = "ready", trig = null, level = 0;
  var RETURN_KEY = "jk-hanashi-return";
  var OPTS = [["はい", 2], ["ときどき", 1], ["いいえ", 0]];
  function show(id) {
    ["hk-quiz", "hk-result"].forEach(function (s) { $(s).hidden = s !== id; });
    document.querySelector(".hk-hero").hidden = !!id;
    window.scrollTo(0, 0);
  }
  function start() { ans = []; i = 0; level = 0; try { sessionStorage.removeItem(RETURN_KEY); } catch (e) {} show("hk-quiz"); renderQ(); }
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
    type = lv === 1 ? "ready" : (pride >= life ? "pride" : "life");
    level = lv;
    renderResult(Object.keys(D.triggers)[0]);
  }
  function renderResult(trigger) {
    $("hk-meter").className = "hk-meter lv" + level;
    $("hk-risk").textContent = ["", "気になるサインは少なめです。", "気になるサインがいくつかあります。早めに話し合いを。", "気になるサインが多めです。できるだけ早く話し合いを。"][level];
    $("hk-type").textContent = D.types[type].name;
    $("hk-type-text").textContent = D.types[type].text;
    pickTrig(trigger);
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
  function setPref(value) {
    document.querySelectorAll(".hk-pref-picker").forEach(function (picker) {
      picker.querySelector(".hk-pref-choice").textContent = D.prefNames[value] || "都道府県を選ぶ";
      picker.querySelectorAll("[data-pref-id]").forEach(function (button) {
        button.setAttribute("aria-pressed", String(button.dataset.prefId === value));
      });
      picker.querySelectorAll("details").forEach(function (details) { details.open = false; });
    });
    var city = $("hk-city");
    city.replaceChildren(new Option(value ? "市町村を選んでください" : "先に都道府県を選んでください", ""));
    D.cities.filter(function (x) { return x.pref === value; }).forEach(function (x) {
      city.add(new Option(x.n, x.slug));
    });
    city.disabled = !value;
    $("hk-city-out").hidden = true;
  }
  document.querySelectorAll("[data-pref-id]").forEach(function (button) {
    button.addEventListener("click", function () {
      var summary = this.closest(".hk-pref-picker").querySelector(".hk-pref-details > summary");
      setPref(this.dataset.prefId);
      summary.focus();
    });
  });
  document.querySelectorAll(".hk-pref-picker").forEach(function (picker) {
    picker.querySelectorAll(".hk-region").forEach(function (region) {
      region.addEventListener("toggle", function () {
        if (region.open) picker.querySelectorAll(".hk-region").forEach(function (other) {
          if (other !== region) other.open = false;
        });
      });
    });
  });
  function cityChanged() {
    var c = D.cities.filter(function (x) { return x.slug === $("hk-city").value; })[0], o = $("hk-city-out");
    if (!c) { o.hidden = true; return; }
    o.hidden = false;
    o.innerHTML = '<h3></h3><p><b></b> <span class="hk-kind"></span></p><p class="hk-what"></p><div class="hk-next-list"></div>';
    o.querySelector("h3").textContent = c.n + "で次に確認すること";
    o.querySelector("b").textContent = "返納後の特典";
    o.querySelector(".hk-kind").textContent = c.k;
    o.querySelector(".hk-kind").classList.toggle("none", !c.has);
    o.querySelector(".hk-what").textContent = c.what;
    var links = [
      ["返納後の特典", c.k, c.n + "の返納後の特典を見る", c.benefitHref, false],
      ["タクシー代の助成", c.taxiKind, c.n + "のタクシー代の助成を確認する", c.taxiHref, false],
      ["免許返納の手続き", c.procedureKind, "免許返納の手続きを確認する", c.procedureHref, c.procedureExternal]
    ];
    links.forEach(function (item) {
      var a = document.createElement(item[3] ? "a" : "div");
      a.className = "hk-next-link";
      if (item[3]) {
        a.href = item[3];
        if (item[4]) { a.target = "_blank"; a.rel = "noopener"; }
        else a.addEventListener("click", saveReturn);
      }
      var title = document.createElement("span"), kind = document.createElement("span"), action = document.createElement("strong");
      title.className = "hk-next-title"; title.textContent = item[0];
      kind.className = "hk-next-kind"; kind.textContent = item[1];
      action.textContent = item[3] ? item[2] + (item[4] ? " ↗ 外部サイト" : " →") : "案内を確認中です";
      a.append(title, kind, action);
      o.querySelector(".hk-next-list").appendChild(a);
    });
  }
  $("hk-city").addEventListener("change", cityChanged);
  function saveReturn() {
    try { sessionStorage.setItem(RETURN_KEY, JSON.stringify({level: level, type: type, trig: trig, pref: D.cities.find(function (x) { return x.slug === $("hk-city").value; }).pref, city: $("hk-city").value})); } catch (e) {}
  }
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
  var fromCity = D.cities.filter(function (x) { return x.slug === from; })[0];
  if (fromCity) {
    setPref(fromCity.pref);
    $("hk-city").value = from;
    cityChanged();
  }
  var navigation = performance.getEntriesByType("navigation")[0];
  if (navigation && navigation.type === "back_forward") {
    try {
      var saved = JSON.parse(sessionStorage.getItem(RETURN_KEY));
      if (saved && D.prefNames[saved.pref] && D.cities.some(function (x) { return x.slug === saved.city && x.pref === saved.pref; })) {
        setPref(saved.pref); $("hk-city").value = saved.city; cityChanged();
        if (saved.level >= 1 && saved.level <= 3 && D.types[saved.type] && D.triggers[saved.trig]) {
          level = saved.level; type = saved.type; renderResult(saved.trig);
        }
      }
    } catch (e) {}
  }
})();
</script>"""
    return shell(
        title="親に免許返納をどう切り出す？最初のひと言を考える｜じもとくらべ",
        description="親の運転が心配な家族へ。免許返納の話をどう切り出すか、6つの質問から最初のひと言の例を探せます。返納後の移動に役立つ、市町村の特典も確認できます。",
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
    <p>このサイトには、会員登録やサイト内の入力フォームはありません。サイトの利用状況を知るために Google アナリティクス 4 を使っています。広告は掲載していません。</p>
  </section>
  <section>
    <h2>アクセス解析</h2>
    <p>Google アナリティクス 4 は、Cookie などを使って、閲覧したページ、アクセス日時、お使いの端末やブラウザ、参照元、ページ内での操作などを記録します。これらの情報は Google に送信され、個人を特定しない形でサイトの改善に利用します。</p>
    <p>Google による情報の取り扱いは<a href="https://policies.google.com/privacy?hl=ja" target="_blank" rel="noopener">Google のプライバシーポリシー</a>をご確認ください。計測を避けたい場合は、<a href="https://tools.google.com/dlpage/gaoptout?hl=ja" target="_blank" rel="noopener">Google アナリティクス オプトアウト アドオン</a>を利用できます。</p>
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
    <p>内容を変えるときは、このページを書き換えて日付を更新します。広告を始めるときは、始める前にこのページに書きます。</p>
  </section>
  <p class="updated">2026年10月3日 更新</p>
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
    bus_file = henno_file.with_name(henno_file.name.replace("-menkyo-henno", "-bus"))
    if bus_file.exists():
        data['bus'] = json.loads(bus_file.read_text(encoding='utf-8'))
    return data


def municipal_mobility_coverage(data, prefs):
    """個別に確認した全国の交通案内を、既存の検索索引に加える。"""
    valid = {(d["pref"]["id"], c["slug"])
             for d in prefs if not d["pref"].get("draft") for c in d["cities"]}
    seen = set()
    entries = []
    for city in data["cities"]:
        key = (city["pref"], city["municipality"])
        if key not in valid or key in seen:
            raise ValueError(f"地域交通データの市区町村が不正または重複: {key}")
        seen.add(key)
        if city["level"] not in {"detailed", "partial"} or not (city["rides"] or city["supports"]):
            raise ValueError(f"地域交通データの掲載範囲または交通候補が不正: {key}")
        for service in [*city["rides"], *city["supports"]]:
            if not service["source"].startswith("https://"):
                raise ValueError(f"地域交通データの出典URLが不正: {key}")
        entries.append({
            "pref": city["pref"], "municipality": city["municipality"],
            "scope": city["scope"], "page": municipal_mobility_path(*key),
            "city": f"{key[0]}:{key[1]}", "level": city["level"],
            "focus": "support" if not city["rides"] else "mobility",
            "hint": city["hint"],
        })
    return entries


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
    mobility = json.loads((ROOT / "data" / "east-harima-mobility.json").read_text(encoding="utf-8"))
    mobility_coverage = json.loads((ROOT / "data" / "mobility-coverage.json").read_text(encoding="utf-8"))
    municipal_mobility = json.loads((ROOT / MUNICIPAL_MOBILITY_DATA_PATH).read_text(encoding="utf-8"))
    all_coverage = {
        "checked": max(mobility_coverage["checked"], municipal_mobility["checked"]),
        "entries": [*mobility_coverage["entries"], *municipal_mobility_coverage(municipal_mobility, prefs)],
    }
    mobility_index = national_mobility_data(prefs, all_coverage, mobility)
    city_coverage = {entry["city"]: entry for entry in mobility_coverage["entries"]
                     if entry["page"].startswith(f"{MOBILITY_CITY_DIR}/")}
    mobility_scopes = {city_id: entry["scope"] for city_id, entry in city_coverage.items()}
    if set(city_coverage) != {c["id"] for c in mobility["cities"]}:
        raise ValueError("地域交通データと掲載範囲の地域IDが一致しません")
    for city_id, entry in city_coverage.items():
        if entry["page"] != mobility_city_path(city_id):
            raise ValueError(f"地域別ページのパスが一致しません: {city_id}")
    data["hk"] = hk
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    guides = [c for c in data["cities"] if c.get("guide")]
    pages = {
        "index.html": top_page(data, a.draft, [d for d in others if not d["pref"].get("draft")], mobility_index),
        NATIONAL_MOBILITY_PATH: national_mobility_page(prefs, all_coverage, mobility, a.draft),
        MOBILITY_PATH: mobility_page(mobility, a.draft, mobility_scopes),
        **{mobility_city_path(c["id"]): mobility_city_page(
            c, city_coverage[c["id"]], data, mobility["cities"], mobility_scopes, mobility["checked"], a.draft)
           for c in mobility["cities"]},
        **{municipal_mobility_path(c["pref"], c["municipality"]): mobility_city_page(
            c, {"scope": c["scope"], "level": c["level"],
                "page": municipal_mobility_path(c["pref"], c["municipality"]),
                "municipality": c["municipality"]},
            next(d for d in prefs if d["pref"]["id"] == c["pref"]),
            [other for other in municipal_mobility["cities"] if other["pref"] == c["pref"]],
            {other["id"]: other["scope"] for other in municipal_mobility["cities"] if other["pref"] == c["pref"]},
            c["checked"], a.draft, regional=False)
           for c in municipal_mobility["cities"]},
        BASIC_GUIDE_PATH: basic_guide_page([data, *others], a.draft),
        list_path(data["pref"]): list_page(data, a.draft, mobility["cities"], mobility_scopes),
        **({taxi_path(data["pref"]): taxi_page(data, a.draft)} if data.get("taxi") else {}),
        **{f"{guide_dir(d['pref'])}/{c['slug']}.html": city_page(c, d, a.draft or d["pref"].get("draft", False))
           for d in [data, *others] for c in d["cities"] if c.get("guide")},
        HANASHI_PATH: hanashi_page(data, hk, a.draft, [data, *[d for d in others if not d["pref"].get("draft")]]),
        "about.html": about_page(a.draft),
        "privacy.html": privacy_page(a.draft),
    }
    # 下書きの県（pref.draft が true）は、検索に出さず、サイトマップとトップにも載せない
    hidden = set()
    for d in [data, *others]:
        if d.get('bus'):
            pages[bus_path(d['pref'])] = bus_page(d, d['bus'], a.draft or d['pref'].get('draft', False), shell, jdate)
            if d['bus'].get('draft') or d['pref'].get('draft'):
                hidden.add(bus_path(d['pref']))
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
    (out / NATIONAL_MOBILITY_DATA_PATH).write_text(
        json.dumps(mobility_index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for d in [data, *others]:
        if d["pref"].get("draft"):
            continue
        city_data = out / "guide-city-data" / f"{d['pref']['id']}.json"
        city_data.parent.mkdir(parents=True, exist_ok=True)
        city_data.write_text(json.dumps(basic_guide_cities(d), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if out.resolve() != ROOT:
        shutil.copy(ROOT / "site.css", out / "site.css")
        if any(d.get('bus') for d in prefs):
            (out / 'assets').mkdir(exist_ok=True)
            shutil.copy(ROOT / 'assets/bus.css', out / 'assets/bus.css')
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
        if any(d.get('bus') for d in prefs):
            (art / 'assets').mkdir(exist_ok=True)
            shutil.copy(ROOT / 'assets/bus.css', art / 'assets/bus.css')
    if (ROOT / 'data/municipality-supplements.json').exists():
        from build_enriched import render
        render(out, draft=a.draft, base_built=True)
    print("built:", ", ".join(pages), "| draft" if a.draft else "")


if __name__ == "__main__":
    main()
