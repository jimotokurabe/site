"""Compare recorded municipal supports without calculating or ranking benefits."""
import json
from pathlib import Path
from bs4 import BeautifulSoup
from seo_content import e, sources as source_rows, return_question, statewide_question, values

KINDS = [('return', '返納した方の特典'), ('bus', 'バス助成・敬老パス'), ('taxi', 'タクシー支援')]
STATES = {'end': '受付終了', 'ended': '終了した制度', 'none': '独自特典なしと記載',
          'notfound': '掲載調査では未確認', 'unknown': '条件など要確認',
          'needs_confirmation': '現在の条件は要確認', 'care': '介護等の条件あり',
          'henno_only': '返納者向け', 'elder': '返納以外の対象もある制度'}


def unique(items):
    result = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return result


def sources(record, inherited, path):
    result = source_rows(record, inherited, path)
    extra = source_rows({'sources': record.get('more_sources', []),
                         'checked': record.get('checked')}, inherited, path)
    for source in extra:
        for key in ('key', 'checked_key'):
            source[key] = source[key].replace('.sources[', '.more_sources[')
    return unique(result + extra)


def fields(record, pairs):
    return [(label, text) for label, key in pairs for text in values(record.get(key))]


def comparison_rows(pref, bus, taxi):
    """Keep source strings whole; every bus program gets its own row."""
    pid = pref['pref']['id']
    unit = pref['pref'].get('unit', '市区町村')
    bus_by_city = {c['slug']: c for c in bus['cities']}
    rows = []
    for city in pref['cities']:
        slug = city['slug']; checked = city.get('checked') or pref['checked']
        a = {'return': city, 'return_checked': checked}
        q = return_question(city, a)
        state = city.get('k', 'unknown')
        guide = city.get('guide', {})
        amount = city.get('amt') if state not in ('end', 'none', 'notfound', 'unknown') else None
        guide_facts = guide.get('facts', [])
        primary = next(((label, text) for label, text in guide_facts
                        if label in ('もらえるもの', '助成の中身', '補助の中身')), None)
        money = [('支援額・期間', amount or STATES.get(state, '金額は掲載情報で未確認')),
                 ('支援内容', q['answer'])]
        # The short source can contain a deposit excluded from guide facts,
        # while the guide can contain annual frequency or personal cost. Keep
        # both visible instead of treating either as a substitute for the other.
        if primary and primary[1] != q['answer']:
            money.append(primary)
        conditions, folded_facts = [], []
        target = next(((label, text) for label, text in guide_facts if '対象' in label), None)
        deadline = next(((label, text) for label, text in guide_facts if '期限' in label and ('申' in label or '申し込' in label)), None)
        if target:
            conditions.append(target)
        elif values(city.get('age')):
            conditions.append(('対象・年齢', city['age']))
        if deadline:
            conditions.append(deadline)
        elif values(city.get('dl')):
            conditions.append(('申請・期限の案内', city['dl']))
        # Keep original labels: a ticket's validity is not an application deadline.
        # Procedure locations and unrelated benefits stay in the disclosure.
        for label, text in guide.get('facts', []):
            if text in [value for _, value in money + conditions]:
                continue
            if any(term in label for term in ('回数', '期間', '有効', '負担')):
                money.append((label, text))
            else:
                folded_facts.append(label + '：' + text)
        rows.append(dict(slug=slug, city=city['n'], kana=city.get('y', ''), region=city['r'], kind='return',
            name=unit + '独自の返納特典・関連支援', state=state,
            money=money, conditions=conditions,
            notes=unique([p['text'] for p in q['cautions']] + values(guide.get('cautions')) + values(city.get('note')) + folded_facts + [city.get('what')]),
            sources=unique(q['sources'] + sources(city, checked, 'return')
                           + sources(guide, guide.get('checked') or checked, 'return.guide')),
            checked=checked, guide_checked=guide.get('checked'), anchor='benefit'))
        b = bus_by_city[slug]
        for p in b.get('programs') or [None]:
            record = p or b; state = (p.get('current') or b['status']) if p else b['status']
            rows.append(dict(slug=slug, city=city['n'], kana=city.get('y', ''), region=city['r'], kind='bus',
                name=p['name'] if p else 'バス助成の掲載状況', state=state,
                relation='免許返納に関連する支援' if p and p.get('kind') == 'henno' else '',
                money=fields(record, [('支援内容・金額', 'benefit'), ('本人負担・運賃', 'fare')]) if p else [('掲載記録', b['summary'])],
                conditions=fields(record, [('対象・条件', 'eligibility')]),
                notes=unique(values(record.get('notes')) + values(b.get('flag'))),
                sources=unique(sources(record, b.get('checked') or bus['checked'], 'bus.program') + sources(b, b.get('checked') or bus['checked'], 'bus')),
                checked=record.get('checked') or b.get('checked') or bus['checked'], anchor='support'))
        t = taxi['cities'][slug]; state = t.get('k', 'unknown')
        money = fields(t, [('支援内容・金額', 'amt'), ('内容', 'what')])
        if state in ('end', 'ended', 'none', 'notfound', 'unknown'):
            label = '独自の助成なしと記載' if state == 'none' else STATES.get(state, '要確認')
            money = [('掲載状況', label)] + fields(t, [('掲載記録', 'what')])
        rows.append(dict(slug=slug, city=city['n'], kana=city.get('y', ''), region=city['r'], kind='taxi',
            name=t.get('name') or 'タクシー支援の掲載状況', state=state, money=money,
            conditions=fields(t, [('対象・条件', 'age'), ('返納との関係', 'henno_link'), ('申請方法・期限', 'how')]),
            notes=unique(values(t.get('note')) + values(t.get('flag')) + values(t.get('guide_details')) + values(t.get('guide_relation_note'))),
            sources=sources(t, t.get('checked') or taxi['checked'], 'taxi'),
            checked=t.get('checked') or taxi['checked'], anchor='taxi'))
    for row in rows:
        row['pref_id'] = pid
    return rows


def dl(pairs):
    return '<dl>' + ''.join('<div><dt>' + e(label) + '</dt><dd>' + e(text) + '</dd></div>' for label, text in pairs) + '</dl>'


def row_html(row):
    state = STATES.get(row['state'], '掲載記録あり・対象条件を確認')
    if row['state'] == 'none' and row['kind'] != 'return':
        state = '独自の助成なしと記載'
    page = row['pref_id'] + '-menkyo-henno/' + row['slug'] + '.html#' + row['anchor']
    evidence = ''.join('<p>' + e(text) + '</p>' for text in row['notes'])
    evidence += '<ul>' + ''.join('<li><a href="' + e(s['url']) + '" data-official-source>' + e(s['label']) + ' ↗</a>'
        '<small>出典の確認日：' + e(s['checked'] or '未記録') + (' ／ 更新日：' + e(s['updated']) if s.get('updated') else '') + '</small></li>' for s in row['sources']) + '</ul>'
    if not row['sources']:
        evidence += '<p>対応する公式出典の記録が不足しています。制度がないという意味ではありません。</p>'
    conditions = row['conditions'] or [('対象・条件', '掲載情報では未確認。詳細・公式窓口で確認してください。')]
    date = '<p class="comparison-date">内容の確認日：' + e(row['checked']) + '</p>'
    if row.get('guide_checked'):
        date += '<p class="comparison-date">手順案内の確認日：' + e(row['guide_checked']) + '</p>'
    return ('<tr data-comparison-row data-city="' + e(row['slug']) + '" data-name="' + e(row['city']) + '" data-kana="' + e(row['kana']) + '" data-region="' + e(row['region']) + '">'
        '<th scope="row"><a href="' + e(page) + '">' + e(row['city']) + '</a><span class="comparison-state">' + e(state) + '</span></th>'
        '<td data-label="支援内容・金額"><strong class="comparison-program">' + e(row['name']) + '</strong>'
        + ('<p class="comparison-relation">現在の条件・金額は確認が必要です。</p>' if row['state'] in ('needs_confirmation', 'unknown') else '')
        + ('<p class="comparison-relation">' + e(row['relation']) + '</p>' if row.get('relation') else '') + dl(row['money']) + '</td>'
        '<td data-label="対象・主な条件">' + dl(conditions) + '</td>'
        '<td data-label="詳細・出典">' + date + '<a class="comparison-detail" href="' + e(page) + '">対象条件・申請先を詳しく →</a>'
        '<details><summary>注意事項・公式出典</summary>' + evidence + '</details></td></tr>')


def enhance_prefecture(body, root, pid):
    root = Path(root)
    pref, bus, taxi = [json.loads((root/'data'/f'{pid}-{suffix}.json').read_text()) for suffix in ('menkyo-henno', 'bus', 'taxi')]
    name = pref['pref']['name']; unit = pref['pref'].get('unit', '市区町村'); count = len(pref['cities'])
    example = '、'.join(city['n'] for city in pref['cities'][:2])
    rows = comparison_rows(pref, bus, taxi)
    soup = BeautifulSoup(body, 'html.parser')
    soup.select_one('h1').string = name + 'の返納特典・交通支援を比べる'
    soup.select_one('.pref-intro > p:last-child').string = f'{count}{unit}の支援内容・金額・対象条件を、支援の種類ごとに並べて確認できます。'
    soup.select_one('.sample-note').string = f'お住まいの{unit}を選び、使いたい支援を比べられます。金額だけでなく、対象・期間・本人負担も合わせて確認してください。'
    label_help = soup.select_one('#label-help'); label_help.extract()
    finder = soup.select_one('.finder')
    finder.select_one('label[for="city-query"]').string = unit + '名で絞り込む'
    finder.select_one('input')['placeholder'] = '例：' + example
    finder.select_one('input')['aria-describedby'] = 'comparison-search-help'
    helper = finder.select_one('p.help'); helper['id'] = 'comparison-search-help'
    helper.string = f'名前・よみがなで絞り込めます。「{example}」のように空白や読点で区切ると、複数の{unit}を並べられます。'
    listing = soup.select_one('section[aria-label="市町村の一覧"]')
    directory = soup.new_tag('details', id='municipal-directory', attrs={'class': 'comparison-directory'})
    summary = soup.new_tag('summary'); summary.string = unit + 'ページを一覧から探す'
    directory.append(summary); listing.wrap(directory); listing.insert(0, label_help)
    controls = '<section class="pref-comparison" id="support-comparison" aria-labelledby="comparison-title" data-municipal-unit="' + e(unit) + '" data-related-support><h2 id="comparison-title">' + e(unit) + 'ごとの支援を比較</h2>'
    controls += '<p>返納特典と通常の高齢者支援を分けて確認できます。居住地・年齢・介護認定などに条件があります。同じ支援が別の欄にも載るため、金額は合算しません。</p>'
    controls += '<fieldset class="comparison-kinds"><legend>比べる支援</legend>' + ''.join('<label><input type="radio" name="comparison-kind" value="' + key + '"' + (' checked' if key == 'return' else '') + '>' + label + '</label>' for key, label in KINDS + [('all', 'すべて')]) + '</fieldset>'
    controls += f'<p id="comparison-count" role="status">{count}{e(unit)}の掲載情報を表示しています。</p><p id="comparison-empty" hidden>一致する{e(unit)}がありません。名前を短くするか、絞り込みを解除してください。</p>'
    for kind, label in KINDS:
        group = [row for row in rows if row['kind'] == kind]
        controls += '<section class="comparison-group" id="comparison-' + kind + '" data-comparison-kind="' + kind + '"><h3>' + label + '</h3>'
        controls += '<table><caption>' + label + '：支援内容・金額・対象条件</caption><thead><tr><th scope="col">' + e(unit) + '</th><th scope="col">支援内容・金額</th><th scope="col">対象・主な条件</th><th scope="col">詳細・出典</th></tr></thead><tbody>'
        controls += ''.join(row_html(row) for row in group) + '</tbody></table></section>'
    controls += '<p class="comparison-note">掲載記録の確認日は出典ごとに異なります。今回の表示改善で全制度を再調査したものではありません。申請期限・除外条件・併用可否・利用範囲は詳細と公式案内で確認してください。</p></section>'
    right = soup.new_tag('div', attrs={'class': 'comparison-results'})
    directory.wrap(right); right.insert(0, BeautifulSoup(controls, 'html.parser'))
    statewide = statewide_question({'statewide': pref['pref'].get('statewide'), 'common': pref.get('common', {}), 'common_checked': pref.get('common', {}).get('checked') or pref['checked']}, name)
    if statewide:
        info = '<details class="comparison-statewide"><summary>' + e(name) + '共通の返納者向け案内（' + e(unit) + '独自の特典とは別）</summary><p>' + e(statewide['answer']) + '</p>'
        info += ''.join('<p>' + e(p['text']) + '</p>' for p in statewide['conditions'])
        info += '<ul>' + ''.join('<li><a href="' + e(source['url']) + '" data-official-source>' + e(source['label']) + ' ↗</a><small>出典の確認日：' + e(source['checked'] or '未記録') + '</small></li>' for source in statewide['sources']) + '</ul></details>'
        soup.select_one('.pref-layout').insert_before(BeautifulSoup(info, 'html.parser'))
    return str(soup)
