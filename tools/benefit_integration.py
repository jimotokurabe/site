"""Connect the compact entrances to intact municipal records.

This is a presentation transform, not a benefit summarizer. It consumes the
already rendered compact page and moves each record once, with no new factual
claims, eligibility parsing, or inferred application/source associations.
"""

import copy
from bs4 import BeautifulSoup

ITEMS = ('benefit', 'support', 'taxi', 'rides')


def fragment(value):
    return BeautifulSoup(value, 'html.parser')


def apply_benefit_integration(soup):
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
    soup.head.append(soup.new_tag('link', rel='stylesheet', href='../assets/benefit-integration.css'))
    browser = soup.new_tag('section', id='benefit-browser', attrs={
        'class': 'benefit-browser', 'aria-label': '支援を選んで条件を確認',
    })
    intro.replace_with(browser)
    intro['class'] = intro.get('class', []) + ['benefit-list']
    browser.append(intro)
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
        panel.append(fragment('<div class="family-actions"><button type="button" data-add-family="' + key +
            '">＋ 家族用メモに追加</button><a href="#family">家族と確認する</a></div>'))
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
        saved = fragment('<div class="family-saved" id="selected-benefits"><h3>選んだ支援を家族用メモに</h3>'
            '<p id="selected-status" role="status">気になる支援の「家族用メモに追加」から選べます。</p>'
            '<div id="selected-list"></div></div>')
        heading = family.find('h2')
        if heading:
            heading.insert_after(saved)
        else:
            family.insert(0, saved)
    soup.body.append(fragment('<dialog id="selection-dialog" aria-labelledby="selection-title">'
        '<form method="dialog"><button aria-label="閉じる">閉じる</button></form>'
        '<h2 id="selection-title">選んだ支援を家族に共有</h2>'
        '<p>掲載記録の条件と出典を含むメモです。利用前に公式案内・窓口で確認してください。</p>'
        '<textarea id="selection-text" rows="13" readonly aria-label="選んだ支援のメモ"></textarea>'
        '<button type="button" id="selection-copy">メモをコピー</button>'
        '<p id="selection-copy-status" role="status"></p></dialog>'
        '<p class="integration-toast" role="status" hidden></p>'))
    soup.body.append(soup.new_tag('script', src='../assets/benefit-integration.js'))
