"""National version of the approved three-city reading layout.

Shared procedures are generated once per prefecture. Municipal records stay on
their own page; this module never transfers municipality-specific guide fields.
"""
import copy
from bs4 import BeautifulSoup
from compact_records import RETURN_PRESENT, TAXI_PRESENT, BUS_PRESENT


def fragment(html):
    return BeautifulSoup(html, 'html.parser')


def apply_compact_city(soup, pid, slug, adopted):
    if 'compact-city' in soup.body.get('class', []):
        return
    soup.body['class'] = soup.body.get('class', []) + ['compact-city']
    soup.head.append(soup.new_tag('link', rel='stylesheet', href='../assets/compact-city.css'))
    # These are generated summaries, not the underlying source records.
    for node in list(soup.select('.warm-answers, .verify-steps, .visual-program-picture, .visual-symbol, .visual-empty-picture')):
        node.decompose()
    for dd in list(soup.select('dd')):
        if dd.get_text(strip=True) in ('記載なし', '未記録', ''):
            dd.parent.decompose()
    for node in list(soup.select('dl, .visual-program')):
        if not node.get_text(strip=True):
            node.decompose()
    # Handcrafted unknown boxes may contain real qualifications. Unwrap only.
    for box in list(soup.select('.unknown')):
        box.unwrap()
    generic_disclaimers = {
        '既存調査で未発見という意味で、すべての助成制度がないと断定するものではありません。',
        '制度がないと断定するものではありません。下の記録・県共通の支援と、公式窓口でご確認ください。',
        '自治体独自のバス助成がないと断定するものではありません。県共通の特典や交通事業者の制度は、それぞれの条件をご確認ください。',
        'すべての助成制度がないと断定するものではありません。',
    }
    for node in list(soup.select('p, h3')):
        text = node.get_text(strip=True)
        if text in generic_disclaimers or text in ('掲載調査では未確認', '市町村独自の返納特典は、掲載調査では未確認'):
            node.decompose()
        elif text.startswith('以下は照合用の記録です。'):
            node.decompose()
    for node in list(soup.find_all(string=True)):
        if '出典の日付：記載なし' in node:
            node.replace_with(str(node).replace('出典の日付：記載なし', ''))

    c = adopted['return']; b = adopted.get('bus') or {}; t = adopted.get('taxi') or {}
    shared = bool(adopted['statewide'] or adopted['common'].get('tokuten'))
    known = {'benefit': c.get('k') in RETURN_PRESENT or shared,
             'support': b.get('status') in BUS_PRESENT,
             'taxi': t.get('k') in TAXI_PRESENT,
             'rides': bool(adopted['mobility'])}
    # The hand-authored partner discount has a distinct source from the negative
    # municipal taxi-grant record. Do not conflate the two kinds of assistance.
    if (pid, slug) == ('hyogo', 'kobe'):
        known['taxi'] = True
    intro = soup.select_one('.intro')
    if not intro:
        raise ValueError(f'Missing purpose navigation: {pid}:{slug}')
    overview = intro.select_one('.overview')
    highlights = soup.new_tag('div', attrs={'class': 'compact-highlights'})
    for li in list(overview.select(':scope > li')):
        link = li.a
        anchor = link['href'].lstrip('#')
        if not known.get(anchor):
            for node in list(link.select('.condition, .value, .arrow')):
                node.decompose()
            continue
        panel = soup.new_tag('a', href=link['href'], attrs={'class': 'compact-highlight'})
        for child in link.select('svg.visual-picture, strong, .condition, .value'):
            panel.append(copy.deepcopy(child))
        if anchor == 'benefit' and c.get('k') not in RETURN_PRESENT and (pid, slug) not in {
                ('hyogo', 'kobe'), ('kanagawa', 'yokohama'), ('kagoshima', 'kagoshima')}:
            for node in list(panel.select('.condition, .value')):
                node.decompose()
            panel.strong.string = '県共通の返納支援'
            panel.append(fragment('<span>特典の一覧と、利用条件を確認 →</span>'))
        for value in panel.select('.value'):
            # Never chop a factual sentence or leave an amount without its limit.
            if len(value.get_text(strip=True)) > 90 or '…' in value.get_text():
                value.clear(); value.string = '支援内容・条件を詳しく見る →'
        for condition in panel.select('.condition'):
            if '…' in condition.get_text():
                condition.string = '対象・利用条件を本文で確認'
        highlights.append(panel)
        li.decompose()
    intro.select_one('h2').string = 'この地域で使える支援を確認' if any(known.values()) else 'この地域の掲載状況を確認'
    intro.select_one('.section-head p').string = '対象・費用・申請先を、目的に合わせて確認できます。'
    if highlights.contents:
        overview.insert_before(highlights)
    if not overview.select('li'):
        overview.decompose()
    intro.append(fragment('<p class="compact-note">掲載がない項目は、制度がないことを示すものではありません。</p>'))
    if not adopted['mobility']:
        rides = soup.select_one('#rides')
        rides.clear()
        rides.append(fragment('<h2>通院・買い物の交通</h2><p>この地域の個別路線・予約方法は、まだ掲載していません。</p>'))
        rides['class'] = ['block', 'compact-status']
    for anchor, present in known.items():
        if not present:
            section = soup.select_one('#' + anchor)
            if section:
                section['class'] = section.get('class', []) + ['compact-status']
    # Put verified prefectural benefits before an unverified municipal record.
    statewide = soup.select_one('article#statewide')
    municipal = soup.select_one('#return-record')
    if statewide and municipal and c.get('k') in ('notfound', 'none', 'end'):
        municipal.insert_before(statewide.extract())


def add_prefecture_procedures(out, prefs):
    from national_city import recursive, date_line, e
    for pid, data in prefs.items():
        path = out / f'{pid}-menkyo-henno.html'
        soup = fragment(path.read_text())
        for old in soup.select('#return-procedure'):
            old.decompose()
        common = data.get('common', {})
        record = {k: v for k, v in common.items() if k not in ('tokuten', 'checked')}
        checked = common.get('checked') or data['checked']
        content = recursive(record, checked)
        if content:
            content += date_line({}, checked)
        else:
            content = '<p>県別の詳しい手続きは、このサイトではまだ掲載していません。</p>'
        section = fragment('<section id="return-procedure" class="compact-prefecture"><h2>' +
            e(data['pref']['name']) + 'の返納手続き・持ち物</h2><p>免許の返納と支援の申請は別の手続きです。支援の対象・期限は、お住まいの市町村の案内で確認してください。</p>' + content +
            '<p><a href="menkyo-henno-guide.html">免許返納の基本ガイド・都道府県警の公式案内 →</a></p></section>')
        soup.main.append(section)
        soup.head.append(soup.new_tag('link', rel='stylesheet', href='assets/compact-city.css'))
        path.write_text(str(soup))
