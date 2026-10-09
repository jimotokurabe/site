"""Shared diagrams made from existing rendered facts, never inferred amounts.

Rows are moved, not summarized: all conditions, cautions, URLs and dates remain
in the document. SVGs are decorative; the original labels explain each panel.
"""
import re
from bs4 import BeautifulSoup


DRAWINGS = {
    'card': '<rect x="32" y="30" width="120" height="71" rx="7" fill="#f6e5e1" transform="rotate(-6 92 65)"/><rect x="42" y="21" width="120" height="73" rx="7" fill="#fffef9"/><circle cx="70" cy="48" r="9"/><path d="M57 74c0-19 27-19 27 0m14-30h48m-48 15h37m-37 16h24"/>',
    'bus': '<path d="M35 103h122"/><rect x="46" y="22" width="100" height="71" rx="17" fill="#e5efdd"/><path d="M48 59h96M95 25v33"/><circle cx="65" cy="93" r="9" fill="#fffef9"/><circle cx="127" cy="93" r="9" fill="#fffef9"/><path d="M60 73h13m48 0h11M36 41v22m119-22v22M76 15h40"/>',
    'taxi': '<path d="M29 103h132M42 62l15-28h72l16 28"/><rect x="35" y="60" width="118" height="34" rx="10" fill="#f6eddb"/><path d="M76 33V22h33v11M46 74h15m65 0h15"/><circle cx="61" cy="96" r="10" fill="#fffef9"/><circle cx="127" cy="96" r="10" fill="#fffef9"/>',
    'route': '<path d="M30 102h131M47 84V51l24-17 24 17v33M60 84V67h21v17M112 86c0-13 38-29 38-49a19 19 0 0 0-38 0c0 20 38 36 38 49"/><circle cx="131" cy="37" r="6"/><path d="M90 101h17m6 0h10"/>',
    'ticket': '<path d="M32 36h126v19a12 12 0 0 0 0 24v19H32V79a12 12 0 0 0 0-24Z" fill="#e5efdd"/><path d="M117 39v11m0 9v11m0 9v15M53 53h43M53 69h34M53 85h20"/>',
    'money': '<rect x="28" y="34" width="134" height="64" rx="5" fill="#f6eddb"/><path d="M41 47h108v38H41Z"/><circle cx="95" cy="66" r="18"/><path d="m86 55 9 11 9-11m-9 11v14m-9-9h18"/>',
    'check': '<rect x="55" y="22" width="86" height="89" rx="8" fill="#e5efdd"/><path d="M81 15h33v16H81z" fill="#fffef9"/><path d="m67 49 5 5 9-11m9 7h32m-55 20 5 5 9-11m9 7h32m-55 20 5 5 9-11m9 7h32"/>',
    'info': '<circle cx="95" cy="63" r="44" fill="#f6eddb"/><path d="M95 57v26M95 40v3"/>',
}
ICONS = {'benefit': 'card', 'support': 'bus', 'taxi': 'taxi', 'rides': 'route'}
KINDS = {'pass': 'card', 'voucher': 'ticket', 'discount': 'money',
         'reimbursement': 'money', 'henno': 'card'}

# Match field labels, not words or numbers within the source prose. Unknown
# labels and nested records are left in place rather than guessed at.
FIELDS = {
    '対象': 'eligibility', '対象・年齢': 'eligibility',
    '対象・条件': 'eligibility', '対象・証明書': 'eligibility',
    '支援内容': 'benefit', '支援の内容': 'benefit', 'もらえるもの': 'benefit',
    '本人負担・運賃': 'fare', '乗るときの負担': 'fare',
    '本人負担': 'fare', '運賃': 'fare',
    '利用できる交通': 'routes', '使える交通': 'routes',
    '利用する交通': 'routes', '利用地域': 'routes',
    '申請・問い合わせ': 'apply', '申請方法': 'apply',
    '申請・必要なもの': 'apply', '申し込み': 'apply',
}
CAUTION_LABELS = {'申請期限', '期限の基準', '対象期間', '申請できる期間',
                  '補足・注意', '確認が必要な点', '手続き前の注意',
                  'まだ確認できていないこと', '利用前に確認すること',
                  '補足', '注意', '申し込み・期限'}
SYMBOLS = {'eligibility': 'check', 'benefit': 'ticket', 'fare': 'money',
           'routes': 'route', 'apply': 'check', 'caution': 'info'}
CAUTION_WORDS = re.compile(r'対象外|除[く外]|限定|のみ|不可|未[確掲載]|確認|注意|終了|期限|締切|まで|以外|条件|併用|必要')


def fold_value(soup, value, title):
    disclosure = soup.new_tag('details', attrs={'class': 'visual-detail'})
    summary = soup.new_tag('summary')
    summary.string = title
    disclosure.append(summary)
    for child in list(value.contents):
        disclosure.append(child.extract())
    value.append(disclosure)


def picture(kind, cls='visual-picture'):
    return BeautifulSoup(
        f'<svg class="{cls}" viewBox="0 0 190 125" aria-hidden="true" '
        'focusable="false" fill="none" stroke="currentColor" stroke-width="2.7" '
        'stroke-linecap="round" stroke-linejoin="round">'
        + DRAWINGS[kind] + '</svg>', 'html.parser').svg


def add_class(tag, *names):
    tag['class'] = list(dict.fromkeys(tag.get('class', []) + list(names)))


def visual_facts(soup, facts, icon):
    """Rearrange flat, original fields in a consistent reading order."""
    rows = []
    for row in facts.find_all('div', recursive=False):
        label = row.find('dt', recursive=False)
        value = row.find('dd', recursive=False)
        if label is None or value is None:
            continue
        title = label.get_text(strip=True)
        category = FIELDS.get(title)
        if title in CAUTION_LABELS or 'important' in row.get('class', []):
            add_class(row, 'visual-condition-row')
        # Source-only records can be disclosed without hiding policy conditions.
        if title in ('公式出典', '追加の出典'):
            fold_value(soup, value, '公式出典・出典ごとの確認日を読む')
        # Structured/nested fields retain their full topology in the original DL.
        if not category or value.select_one('dl, ul, ol, details'):
            continue
        rows.append((category, row, label))
    if not rows:
        return
    panel = soup.new_tag('div', attrs={'class': 'visual-program'})
    art = soup.new_tag('div', attrs={'class': 'visual-program-picture'})
    art.append(picture(icon))
    caption = soup.new_tag('p', attrs={'class': 'visual-program-caption'})
    caption.string = '制度の要点'
    art.append(caption)
    panel.append(art)
    grid = soup.new_tag('dl', attrs={'class': 'visual-facts'})
    order = {'eligibility': 0, 'benefit': 1, 'fare': 2, 'routes': 3, 'apply': 4}
    for category, row, label in sorted(rows, key=lambda x: order[x[0]]):
        add_class(row, 'visual-fact', 'visual-fact-' + category)
        label.insert(0, picture(SYMBOLS[category], 'visual-symbol'))
        value = row.find('dd', recursive=False)
        text = value.get_text(' ', strip=True)
        if category in ('routes', 'apply') and len(text) > 180 and not CAUTION_WORDS.search(text):
            fold_value(soup, value, '詳しい' + label.get_text(strip=True) + 'を読む')
        grid.append(row.extract())
    panel.append(grid)
    facts.insert_before(panel)
    if not facts.find_all('div', recursive=False):
        facts.decompose()


def apply_visual_city(soup, adopted):
    if soup.select_one('link[href="../assets/visual-city.css"]'):
        return
    soup.head.append(soup.new_tag('link', rel='stylesheet', href='../assets/visual-city.css'))
    for anchor, icon in ICONS.items():
        for choice in soup.select(f'.overview a[href="#{anchor}"]'):
            add_class(choice, 'visual-choice', 'visual-choice-' + anchor)
            choice.insert(0, picture(icon))
        section = soup.find(id=anchor)
        if section is None:
            continue
        add_class(section, 'visual-section')
        heading = section.find('h2', recursive=False)
        if heading:
            header = soup.new_tag('div', attrs={'class': 'visual-section-head'})
            heading.insert_before(header)
            header.append(heading.extract())
            header.append(picture(icon))
        # Unknown/ended records still receive a navigable illustration but no
        # assumed entitlement, fabricated use sequence or numeric calculation.
        record = adopted.get({'benefit': 'return', 'support': 'bus', 'taxi': 'taxi'}.get(anchor, ''))
        state = (record or {}).get('status') or (record or {}).get('k')
        if state in ('end', 'ended'):
            add_class(section, 'visual-state', 'visual-state-ended')
        elif state in ('notfound', 'unknown') or (anchor != 'rides' and not record):
            add_class(section, 'visual-state', 'visual-state-unknown')
        for unknown in section.select('.unknown'):
            add_class(unknown, 'visual-empty')
            unknown.insert(0, picture('info', 'visual-empty-picture'))
        programs = (adopted.get('bus') or {}).get('programs', []) if anchor == 'support' else []
        for facts in list(section.select('dl.facts')):
            # Never change historical archive material, nested DLs, or closed
            # source records. Their exact text and source dates stay intact.
            if facts.find_parent(['dl', 'details']) or facts.find_parent(class_='archive'):
                continue
            local_icon = icon
            container = facts.find_parent(class_='subprogram')
            if container and programs:
                name = container.find(['h3', 'h4'])
                program = next((p for p in programs if name and p.get('name') == name.get_text(strip=True)), None)
                if program:
                    local_icon = KINDS.get(program.get('kind'), icon)
            visual_facts(soup, facts, local_icon)
