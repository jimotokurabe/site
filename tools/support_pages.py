"""市町村を一度選び、返納・バス・タクシーの支援を同じ欄で読む。"""
from html import escape as e
from bus_pages import KINDS, STATUS


def panel(label, teaser, body, tone, marker=""):
    return (f'<details class="support-panel support-{tone}"><summary>'
            f'<span class="support-label">{e(label)}</span>'
            f'<span class="support-teaser">{e(teaser)}</span>'
            f'<span class="support-action">詳細を開く</span></summary>'
            f'<div class="support-body">{marker}{body}</div></details>')


def bus_panel(city, checked):
    programs = []
    for p in city['programs']:
        facts = ''.join(f'<div><dt>{label}</dt><dd>{e(p[field])}</dd></div>' for field, label in
                        [('eligibility', '対象・条件'), ('benefit', '助成の中身'),
                         ('fare', '乗るときの料金'), ('routes', '使えるバス'), ('apply', '申し込み')])
        warning = '<p class="flag">現在の条件を確認できていない項目があります。下の確認先をご覧ください。</p>' if p.get('current') == 'needs_confirmation' else ''
        notes = ''.join(f'<li>{e(n)}</li>' for n in p['notes'])
        programs.append(f'<section class="bus-program"><h4>{e(p["name"])} <span class="chip">{KINDS[p["kind"]]}</span></h4>{warning}<dl class="facts">{facts}</dl>'
                        + (f'<ul>{notes}</ul>' if notes else '') + '</section>')
    sources = {s['url']: s for s in [*city.get('sources', []), *(s for p in city['programs'] for s in p['sources'])]}
    links = ''.join(f'<li><a href="{e(s["url"])}" target="_blank" rel="noopener">{e(s["label"])} ↗</a><span class="dates">ページの日付：{e(s.get("updated") or "記載なし")} ／ 確認：{e(s["checked"])}</span></li>' for s in sources.values())
    flag = f'<p class="flag">確認が必要な点：{e(city["flag"])}</p>' if city.get('flag') else ''
    body = f'<p class="support-status">{STATUS[city["status"]]} ／ {e(checked)}確認</p>' + ''.join(programs) + flag + f'<ul class="bus-sources">{links}</ul>'
    return panel('バス助成・敬老パス', city['summary'], body, 'bus')


def integrated_main(data, sections, statewide, extras, jdate):
    pref = data['pref']; total = len(data['cities']); unit = pref['unit']
    area = '都内' if pref['id']=='tokyo' else '府内' if pref['id'] in {'osaka','kyoto'} else '県内'
    options = ''.join(f'<option value="{e(r["id"])}">{e(r["name"])}</option>' for r in data['regions'])
    common = data['bus'].get('common')
    common_html = f'<p>{e(common.get("summary", common.get("note", "県内共通のバス割引の対象・条件は、公式案内で確認してください。")))}</p><p><a href="{e(common["url"])}" target="_blank" rel="noopener">{e(common["label"])} ↗</a></p><p class="dates">{e(common["checked"])}確認</p>' if common else ''
    return f'''<nav class="crumbs" aria-label="いまいる場所"><a href="./">トップ</a> ＞ {e(pref['name'])}の返納特典・交通費の支援</nav>
<header class="support-hero"><p class="eyebrow">{e(pref['name'])}・{total}{e(unit)}</p>
<h1>免許返納の特典と、<br>バス・タクシーの助成。</h1>
<p class="lead">お住まいのまちを選ぶと、3つの支援をまとめて確認できます。返納しなくても使える高齢者向けの支援も掲載しています。</p>
<div class="support-key" aria-label="比べられる支援"><span>免許返納の特典</span><span>バス助成</span><span>タクシー助成</span></div>
<p class="dates">確認日：返納特典 {jdate(data['checked'])} ／ バス {jdate(data['bus']['checked'])} ／ タクシー {jdate(data.get('taxi_checked', data['checked']))}</p></header>
<section class="support-search" id="pick" aria-labelledby="pick-h"><h2 id="pick-h">お住まいのまちを探す</h2>
<div class="support-inputs"><div><label for="q">市町村の名前（ひらがなでも検索）</label><input id="q" type="search" autocomplete="off" placeholder="{e(pref.get('placeholder', '市町村名を入力'))}"></div><div><label for="support-region">地域で絞る</label><select id="support-region"><option value="">すべての地域</option>{options}</select></div></div>
<div class="filters" id="filters" role="group" aria-label="案内のある支援で絞る"><button data-f="all" aria-pressed="true" type="button">すべて</button><button data-f="return" aria-pressed="false" type="button">返納特典・返納後の支援あり</button><button data-f="bus" aria-pressed="false" type="button">バス支援の案内あり</button><button data-f="taxi" aria-pressed="false" type="button">タクシー支援の案内あり</button></div>
<p id="count" data-unit="{e(unit)}" role="status">{total}{e(unit)}を表示しています。</p><p id="support-empty" hidden>該当する市町村がありません。名前や絞り込みを変えてください。</p></section>
<p class="support-help">各欄を開くと、対象条件・金額・申請方法を読めます。同じ制度が複数の欄に載ることがあるため、金額を足し合わせないでください。「案内あり」は全員が対象という意味ではありません。「記載なし」は制度がないという意味ではありません。</p>
<h2 class="section-title" id="list-h">市町村ごとの支援</h2>{''.join(sections)}
<details class="support-common" id="statewide"><summary>{area}共通の特典・割引を見る</summary>{statewide.replace('id="statewide"', 'id="statewide-details"')}{common_html}</details>
{extras}
<section class="about-list"><h2>利用する前に確認してください</h2><p>支援ごとに年齢、住所、免許返納の要否、申請期限が異なります。現在の条件を確認できない点は各欄に確認先を記載しています。申請や利用の前に公式窓口へ確認してください。</p><p><a href="menkyo-henno-guide.html">免許返納の手続き・基本ガイド</a> ／ <a href="{pref['id']}-bus.html">バス助成だけを比べる</a> ／ <a href="{pref['id']}-taxi.html">タクシー助成だけを比べる</a></p></section>'''


SCRIPT = r'''<script>
(function(){
 const q=document.getElementById('q'), region=document.getElementById('support-region');
 const cards=Array.from(document.querySelectorAll('.support-page .card'));
 const buttons=Array.from(document.querySelectorAll('#filters button'));let selected='all';
 const norm=s=>s.normalize('NFKC').toLowerCase().replace(/[ァ-ヶ]/g,c=>String.fromCharCode(c.charCodeAt(0)-96)).replace(/\s/g,'');
 function apply(){let shown=0;const query=norm(q.value);
  cards.forEach(c=>{const hit=(!query||norm(c.dataset.search).includes(query))&&(!region.value||c.dataset.region===region.value)&&(selected==='all'||c.dataset[selected]==='true');c.hidden=!hit;if(hit)shown++;});
  document.querySelectorAll('.support-page .region').forEach(r=>r.hidden=!r.querySelector('.card:not([hidden])'));
  document.getElementById('count').textContent=cards.length+document.getElementById('count').dataset.unit+'のうち '+shown+document.getElementById('count').dataset.unit+'を表示しています。';
  document.getElementById('support-empty').hidden=shown>0;
  buttons.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.f===selected)));
 }
 q.addEventListener('input',apply);region.addEventListener('change',apply);
 buttons.forEach(b=>b.addEventListener('click',()=>{selected=b.dataset.f;apply();}));
 document.querySelectorAll('.support-panel').forEach(d=>d.addEventListener('toggle',()=>d.querySelector('.support-action').textContent=d.open?'詳細を閉じる':'詳細を開く'));
 function reveal(){let id;try{id=decodeURIComponent(location.hash.slice(1));}catch(e){return;}const target=document.getElementById(id);if(target&&target.matches('details'))target.open=true;if(target&&target.matches('.card')){q.value='';region.value='';selected='all';apply();target.scrollIntoView();}}
 window.addEventListener('hashchange',reveal);apply();reveal();
})();</script>'''
