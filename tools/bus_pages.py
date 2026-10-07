"""市町村の高齢者バス支援。県を追加しても同じデータ形式と画面を使う。"""
from collections import Counter
from datetime import date
from html import escape
import hashlib
from pathlib import Path
from urllib.parse import urlparse


STATUS = {
    "active": "高齢者向けの案内", "henno": "返納した人への支援",
    "notfound": "記載なし", "unknown": "要確認", "ended": "終了", "none": "なし",
}
KINDS = {"pass": "乗車証", "discount": "運賃割引", "voucher": "乗車券",
         "reimbursement": "購入・利用費の助成", "henno": "免許返納が条件"}

# 県の公式市町村リンクで確認したHTTP専用サイト。読めないHTTPSへ置換しない。
HTTP_OFFICIAL_HOSTS = {"town.mihama.wakayama.jp", "town.wakayama-hidaka.lg.jp", "town.yura.wakayama.jp", "vill.shinjo.okayama.jp", "town.anan.nagano.jp", "vill.miyada.nagano.jp", "vill.sakae.nagano.jp", "town.minamitane.kagoshima.jp", "town.toyo.kochi.jp", "bus.saga.saga.jp", "town.itano.tokushima.jp"}


def valid_source_url(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").removeprefix("www.")
    return bool(parsed.netloc and (parsed.scheme == "https" or
                (parsed.scheme == "http" and (host.endswith(".lg.jp") or host in HTTP_OFFICIAL_HOSTS))))


def validate_bus(data, pref_data):
    """欠落自治体・根拠のない現行表示・データ型の誤りを生成前に止める。"""
    date.fromisoformat(data["checked"])
    assert isinstance(data.get("draft", False), bool), "draft must be boolean"
    common = data.get("common", {})
    if common:
        assert urlparse(common["url"]).scheme == "https" and urlparse(common["url"]).netloc
        assert common.get("label"), "common label required"
        date.fromisoformat(common["checked"])
    expected = {c["slug"]: c["n"] for c in pref_data["cities"]}
    rows = data["cities"]
    actual = [c["slug"] for c in rows]
    assert len(actual) == len(set(actual)), "duplicate municipality"
    assert set(actual) == set(expected), "municipality coverage mismatch"
    for c in rows:
        assert c["name"] == expected[c["slug"]], c["slug"] + ": name mismatch"
        assert c["status"] in STATUS, "invalid status"
        assert isinstance(c["programs"], list), "programs must be a list"
        assert c.get("summary"), "summary required"
        if c["status"] in {"active", "henno"}:
            assert c["programs"], c["slug"] + ": active without program"
        else:
            assert not c["programs"], c["slug"] + ": unconfirmed active program"
        if c["status"] == "henno":
            assert all(p["kind"] == "henno" for p in c["programs"])
        if c["status"] == "active":
            assert any(p["kind"] != "henno" for p in c["programs"])
        sources = list(c.get("sources", []))
        for p in c["programs"]:
            assert p["kind"] in KINDS
            assert p["current"] in {"document_checked", "needs_confirmation"}, "invalid current state"
            if p["current"] == "needs_confirmation":
                assert c.get("flag"), "unconfirmed program requires contact guidance"
            age = p["age_min"]
            assert age is None or (type(age) is int and 0 <= age <= 120)
            for field in ("name", "eligibility", "benefit", "fare", "routes", "apply"):
                assert isinstance(p[field], str) and p[field].strip(), f"{c['slug']}: {field} required"
            assert isinstance(p["notes"], list) and all(isinstance(n, str) for n in p["notes"])
            assert p["sources"], c["slug"] + ": source required"
            sources.extend(p["sources"])
        if c["status"] in {"none", "ended"}:
            assert c.get("sources"), "explicit none/ended requires source"
        for s in sources:
            assert valid_source_url(s["url"]), "invalid source URL"
            date.fromisoformat(s["checked"])
            assert s.get("label"), "source label required"
            updated = s.get("updated", "")
            if updated:
                date.fromisoformat(updated)
            if not updated or (date.fromisoformat(data["checked"]) - date.fromisoformat(updated)).days > 365:
                assert c.get("flag"), c["slug"] + ": old/undated source requires flag"
        if c["status"] in {"unknown", "notfound"}:
            assert c.get("flag"), c["slug"] + ": contact guidance required"


def bus_path(pref):
    return f"{pref['id']}-bus.html"


def bus_page(pref_data, bus, draft, shell, jdate):
    validate_bus(bus, pref_data)
    css_rev = hashlib.sha256((Path(__file__).resolve().parent.parent / 'assets/bus.css').read_bytes()).hexdigest()[:12]
    e = lambda s: escape(str(s), quote=True)
    pref = pref_data["pref"]
    by_slug = {c["slug"]: c for c in bus["cities"]}
    counts = Counter(c["status"] for c in bus["cities"])
    total = len(by_slug)
    regions = pref_data["regions"]
    options = ''.join(f'<option value="{e(r["id"])}">{e(r["name"])}</option>' for r in regions)
    filters = ''.join(f'<button type="button" data-bus-filter="{value}" aria-pressed="{str(value == "all").lower()}">{label}</button>'
                      for value, label in [("all", "すべて"), ("active", "高齢者向け支援"), ("henno", "返納が条件"),
                                           ("unverified", "記載なし・要確認"), ("ended", "終了・なし")])
    sections = []
    for region in regions:
        cards = []
        for city in pref_data["cities"]:
            if city["r"] != region["id"]:
                continue
            c = by_slug[city["slug"]]
            programs = []
            for p in c["programs"]:
                facts = ''.join(f'<div><dt>{label}</dt><dd>{e(p[field])}</dd></div>' for field, label in
                                [("eligibility", "対象・条件"), ("benefit", "助成の中身"), ("fare", "乗るときの料金"),
                                 ("routes", "使えるバス"), ("apply", "申し込み")])
                notes = ''.join(f'<li>{e(n)}</li>' for n in p["notes"])
                current_note = '<p class="flag">この制度には、現在の条件・金額を確認できていない項目があります。下の注意と確認先をご覧ください。</p>' if p.get('current') == 'needs_confirmation' else ''
                programs.append(f'<section class="bus-program"><h4>{e(p["name"])}<span class="chip">{KINDS[p["kind"]]}</span></h4>{current_note}'
                                f'<dl class="facts">{facts}</dl>' + (f'<ul class="bullets">{notes}</ul>' if notes else '') + '</section>')
            all_sources = [*c.get("sources", []), *(s for p in c["programs"] for s in p["sources"])]
            sources = {s["url"]: s for s in all_sources}
            links = ''.join(f'<li><a href="{e(s["url"])}" target="_blank" rel="noopener">{e(s["label"])} ↗</a>'
                            f'<span class="dates">ページの日付：{e(s.get("updated") or "記載なし")} ／ 確認：{e(s["checked"])}</span></li>'
                            for s in sources.values())
            flag = f'<p class="flag">確認が必要な点：{e(c["flag"])}</p>' if c.get("flag") else ''
            henno = any(p["kind"] == "henno" for p in c["programs"])
            unverified = c['status'] in {'notfound', 'unknown'} or any(p.get('current') == 'needs_confirmation' for p in c['programs'])
            search = e(city['n'] + ' ' + city['y'] + ' ' + city['slug'])
            cards.append(f'''<article class="card bus-card{' is-notfound' if c['status'] in {'notfound', 'unknown'} else ''}" id="{city['slug']}"
 data-status="{c['status']}" data-henno="{str(henno).lower()}" data-unverified="{str(unverified).lower()}" data-region="{region['id']}" data-search="{search}" aria-labelledby="{city['slug']}-h">
 <div class="card-head"><h3 class="city" id="{city['slug']}-h">{e(city['n'])}<span class="yomi">{e(city['y'])}</span></h3><span class="chip">{STATUS[c['status']]}</span></div>
 <p class="what">{e(c['summary'])}</p>{''.join(programs)}{flag}
 <ul class="bus-sources">{links}</ul>
 <p class="note"><a href="{pref['id']}-menkyo-henno.html#{city['slug']}">免許返納の特典も見る</a></p>
 <p class="card-back"><a href="#pick">↑ 絞り込みに戻る</a></p></article>''')
        sections.append(f'<section class="region bus-region" aria-labelledby="r-{region["id"]}"><div class="region-head">'
                        f'<h2 id="r-{region["id"]}">{e(region["name"])}</h2></div>{"".join(cards)}</section>')
    common = bus.get('common', {})
    common_link = (f'<p><a href="{e(common["url"])}" target="_blank" rel="noopener">{e(common["label"])}</a>も別に確認できます。</p>'
                   if common.get('url') else '')
    taxi_link = f'<a href="{pref["id"]}-taxi.html">高齢者のタクシー助成</a> ／ ' if pref_data.get('taxi') else ''
    main = f'''<nav class="crumbs" aria-label="いまいる場所"><a href="./">トップ</a> ＞ {e(pref['name'])}の高齢者バス助成</nav>
<div class="hero"><p class="eyebrow">{e(pref['name'])}・{total}{e(pref['unit'])} ／ {jdate(bus['checked'])}確認</p>
<h1>高齢者のバス代、<br>住むまちでどう違う？</h1>
<p class="lead">敬老パス・運賃の割引・バス券の助成を、対象、助成の中身、料金、使えるバス、申し込みの5項目で比べられます。</p></div>
<section class="pick" id="pick" aria-labelledby="pick-h"><h2 class="section-title" id="pick-h">お住まいのまちを探す</h2>
<div class="bus-controls"><div class="search"><label for="bus-q">市町村の名前（ひらがなでも検索）</label><input id="bus-q" type="search" autocomplete="off" placeholder="{e(pref.get('placeholder', '例：あかし、神戸'))}"></div>
<div class="search"><label for="bus-region">地域で絞る</label><select id="bus-region"><option value="">すべての地域</option>{options}</select></div></div>
<div class="filters" role="group" aria-label="支援の種類で絞る">{filters}</div>
<p class="count" id="bus-count" aria-live="polite">{total}{e(pref['unit'])}を表示しています。</p><p id="bus-empty" hidden>条件に合う市町村がありません。名前や絞り込みを変えてください。</p></section>
<p class="note">高齢者向け支援の案内は<strong>{counts['active']}{e(pref['unit'])}</strong>で見つかりました。「記載なし」は制度がないという意味ではありません。古い資料による条件・金額は、各欄に「未確認」と表示しています。</p>
<details class="bus-scope"><summary>掲載する制度と、県内共通の特典について</summary>
<p>路線・コミュニティバス等の乗車料金の支援を比べています。免許返納だけが条件の支援は別に表示しています。一般の住民に共通の運賃、障害者向けだけの制度、タクシー券だけの助成、民間バス会社独自のシニア定期券、福祉バスの貸切使用は、この乗車料金の比較には含めていません。</p>
{common_link}</details>
{''.join(sections)}
<section class="about-list"><h2>調べ方と、確認が必要な点</h2><ul class="bullets">
<li>市町村の公式ページを検索し、読めた本文と資料に基づいて記載しました。確認できなかった点は各市町村の欄に残しています。</li>
<li>「なし」は公式に制度がないと明記された場合だけ、「終了」は終了が明記された場合だけ使います。</li>
<li>古い資料や日付のない資料、制度の条件が曖昧な場合は、申し込む前に市町村の窓口で確認してください。</li>
<li>{taxi_link}<a href="{pref['id']}-menkyo-henno.html">免許返納の特典</a></li>
</ul></section>'''
    return shell(title=f"{pref['name']}の高齢者バス助成・敬老パス {total}{pref['unit']}比較｜じもとくらべ",
                 description=f"{pref['name']}の高齢者バス助成・敬老パスを対象、料金、使える路線、申し込みで比較。{total}{pref['unit']}の公式資料を調査し、未確認の点も表示。{jdate(bus['checked'])}確認。",
                 path=bus_path(pref), main=main, draft=draft or bus.get("draft", False), scripts=BUS_SCRIPT,
                 draft_note=f"制度の内容を確認するための{pref['name']}版です。", page_class="bus-page",
                 styles=f'\n<link rel="stylesheet" href="assets/bus.css?v={css_rev}">')


BUS_SCRIPT = r'''<script>
(function () {
  var cards = Array.from(document.querySelectorAll('.bus-card'));
  var query = document.getElementById('bus-q'), region = document.getElementById('bus-region');
  var filter = 'all', buttons = document.querySelectorAll('[data-bus-filter]');
  function normalize(s) { return s.normalize('NFKC').toLowerCase().replace(/[ァ-ヶ]/g, function(c){return String.fromCharCode(c.charCodeAt(0)-0x60);}).replace(/\s/g, ''); }
  function apply() {
    var q = normalize(query.value), shown = 0;
    cards.forEach(function(c) {
      var status = c.dataset.status;
      var kind = filter === 'all' || (filter === 'henno' ? c.dataset.henno === 'true' :
        filter === 'unverified' ? c.dataset.unverified === 'true' :
        filter === 'ended' ? ['ended','none'].includes(status) : status === filter);
      c.hidden = !(kind && (!region.value || region.value === c.dataset.region) && normalize(c.dataset.search).includes(q));
      if (!c.hidden) shown++;
    });
    document.querySelectorAll('.bus-region').forEach(function(r){r.hidden = !r.querySelector('.bus-card:not([hidden])');});
    document.getElementById('bus-count').textContent = cards.length + '市町村のうち ' + shown + '市町村を表示しています。';
    document.getElementById('bus-empty').hidden = shown !== 0;
    buttons.forEach(function(b){b.setAttribute('aria-pressed', String(b.dataset.busFilter === filter));});
  }
  buttons.forEach(function(b){b.addEventListener('click', function(){filter=b.dataset.busFilter;apply();});});
  query.addEventListener('input', apply); region.addEventListener('change', apply);
  function fromHash() {
    var target = document.getElementById(location.hash.slice(1));
    if (target && target.classList.contains('bus-card')) {
      query.value = ''; region.value = ''; filter = 'all'; apply(); target.scrollIntoView();
    }
  }
  window.addEventListener('hashchange', fromHash); apply(); fromHash();
})();
</script>'''
