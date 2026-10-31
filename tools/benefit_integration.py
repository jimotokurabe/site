"""Connect the compact entrances to intact municipal records.

This is a presentation transform, not a benefit summarizer. It consumes the
already rendered compact page and moves each record once, with no new factual
claims, eligibility parsing, or inferred application/source associations.
"""

import copy
from urllib.parse import urlencode
from bs4 import BeautifulSoup

ITEMS = ('benefit', 'support', 'taxi', 'rides')


def fragment(value):
    return BeautifulSoup(value, 'html.parser')


def apply_benefit_integration(soup, pref_id=None, city_slug=None, *, estimate_available=False):
    """Enhance four existing entrances; without JS every record remains visible."""
    if soup.select_one('#benefit-browser'):
        return
    intro = soup.select_one('.intro')
    records = {key: soup.select_one('#' + key) for key in ITEMS}
    if intro is None or any(record is None for record in records.values()):
        raise ValueError('Benefit integration requires the compact intro and four records')
    choices = intro.select('a.compact-highlight[href], .overview > li > a[href]')
    order = []
    for choice in choices:
        key = choice['href'].removeprefix('#')
        if choice['href'] != '#' + key or key not in ITEMS:
            continue
        if key in order:
            raise ValueError('Duplicate compact entrance: ' + key)
        order.append(key)
        choice['data-pick'] = key
        choice['class'] = choice.get('class', []) + ['benefit-card']
        if choice.find_parent(class_='overview'):
            choice['class'].append('is-unknown')
        choice['aria-controls'] = key
    if set(order) != set(ITEMS):
        raise ValueError('Benefit integration requires exactly four compact entrances')

    soup.body['class'] = soup.body.get('class', []) + ['integrated-city']
    soup.head.append(soup.new_tag('link', rel='stylesheet', href='../assets/benefit-integration.css?v=family-memo-20261031'))
    browser = soup.new_tag('section', id='benefit-browser', attrs={
        'class': 'benefit-browser', 'aria-label': '支援を選んで条件を確認',
    })
    intro.replace_with(browser)
    intro['class'] = intro.get('class', []) + ['benefit-list']
    browser.append(intro)
    intro.append(fragment('<p class="family-entry"><a href="#family">家族用メモ・共有の使い方 →</a>'
        '<small>気になる支援の条件や出典を、コピーして家族に伝えられます。</small></p>'))
    if pref_id is not None and city_slug is not None:
        destination = 'transport-cost.html' if estimate_available else 'outing-plan.html'
        href = '../' + destination + '?' + urlencode({'pref': pref_id, 'city': city_slug})
        estimate = soup.new_tag('p', attrs={'class': 'cross transport-cost-link'})
        link = soup.new_tag('a', href=href)
        link.string = ('この地域の移動費の目安を見る →' if estimate_available
                       else '行き先と往復の費用を整理する →')
        estimate.append(link)
        if not estimate_available:
            note = soup.new_tag('small', attrs={'class': 'estimate-note'})
            note.string = 'この地域は自動試算に未対応です。調べた交通手段と費用を、お出かけ計画にまとめられます。'
            estimate.append(note)
        browser.insert_before(estimate)
    panels = soup.new_tag('div', attrs={'class': 'benefit-panels'})
    browser.append(panels)
    for key in order:
        panel = records[key].extract()
        panel['class'] = panel.get('class', []) + ['integrated-panel']
        panel['tabindex'] = '-1'
        # Retain every original child, in order, without copying its text. IDs
        # inside the record remain available for old incoming deep links.
        original = soup.new_tag('div', id='record-' + key, attrs={'class': 'original-record'})
        for child in list(panel.contents):
            original.append(child.extract())
        heading = original.find('h2')
        if heading:
            if not heading.get('id'):
                heading['id'] = 'integration-title-' + key
            panel['aria-labelledby'] = heading['id']
        panel.append(fragment('<a class="panel-return" href="#benefit-browser">← 支援の一覧に戻る</a>'))
        panel.append(original)
        # A record may contain multiple programs and source URLs. Do not pick
        # one URL as an application action without verified program ownership.
        panel.append(fragment('<div class="family-actions"><h3>この支援を、家族と確認</h3>'
            '<p>対象条件・申請先・公式出典をひとつのメモに。コピーして、LINEやメールなどに貼り付けられます。</p>'
            '<div class="family-action-buttons"><button type="button" data-share-benefit="' + key +
            '">この支援のメモを確認・コピー</button><button type="button" data-add-family="' + key +
            '">＋ 家族用メモに追加</button></div>'
            '<a href="#family" data-selected-summary>複数の支援をまとめる・確認項目を見る →</a></div>'))
        panels.append(panel)

    # Some templates keep the empty legacy county anchor outside the section.
    # Nest it with the same benefit so native and enhanced deep links agree.
    for alias in ('statewide', 'sw-h'):
        node = soup.select_one('#' + alias)
        if node and not node.find_parent(class_='integrated-panel') and not node.get_text(strip=True):
            soup.select_one('#record-benefit').insert(0, node.extract())

    procedure = soup.select_one('#procedure')
    if procedure:
        county = next((a for a in procedure.select('a[href]')
                       if a['href'].endswith('#return-procedure')), None)
        if county:
            jump = soup.new_tag('div', attrs={'class': 'procedure-jump'})
            jump.append(copy.deepcopy(county))
            browser.insert_after(jump)
        retained = soup.new_tag('details', attrs={'class': 'retained-procedure'})
        retained.append(fragment('<summary>市町村の手順・窓口を詳しく確認</summary>'))
        procedure.replace_with(retained)
        retained.append(procedure)

    family = soup.select_one('#family')
    if family:
        family['tabindex'] = '-1'
        saved = fragment('<div class="family-saved" id="selected-benefits"><h3>選んだ支援をまとめて共有</h3>'
            '<p>各支援の「家族用メモに追加」でまとめられます。メモをコピーしたら、LINEやメールなどに貼り付けて家族と確認できます。</p>'
            '<p id="selected-status" role="status">各支援の「家族用メモに追加」を選ぶと、対象条件と出典をまとめてコピーできます。</p>'
            '<div id="selected-list"></div><a class="family-back" href="#benefit-browser">ほかの支援を選ぶ →</a></div>')
        lead = family.select_one('.lead')
        if lead:
            lead.string = '対象条件・費用・申請先・必要書類を本人や家族と確認し、公式窓口に相談するときに活用できます。'
        heading = family.find('h2')
        if heading:
            heading.insert_after(saved)
        else:
            family.insert(0, saved)
    soup.body.append(fragment('<dialog id="selection-dialog" aria-labelledby="selection-title">'
        '<form method="dialog"><button aria-label="閉じる">閉じる</button></form>'
        '<h2 id="selection-title">家族と確認する共有メモ</h2>'
        '<p>下の内容をコピーして、LINEやメールなどに貼り付けられます。対象条件・出典・確認日を含むメモです。申請・利用前に公式案内や窓口で最新の内容をご確認ください。</p>'
        '<textarea id="selection-text" rows="13" readonly aria-label="選んだ支援のメモ"></textarea>'
        '<button type="button" id="selection-copy">メモをコピー</button>'
        '<p id="selection-copy-status" role="status"></p></dialog>'
        '<p class="integration-toast" role="status" hidden></p>'))
    soup.body.append(soup.new_tag('script', src='../assets/benefit-integration.js?v=shared-conditions-20261031'))
