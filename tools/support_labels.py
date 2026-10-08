"""Conservative navigation labels from municipality records, not prefecture benefits.

Labels describe published evidence, not an individual visitor's eligibility.
Unknown/ended records never receive an affirmative label. Existing warnings stay
visible as '要確認'; transport alone is not treated as a taxi subsidy.
"""
import re
import unicodedata
from datetime import date

POSITIVE_RETURN = {'give', 'discount', 'purchase'}
POSITIVE_TAXI = {'yes', 'care', 'henno_only'}


def label(kind, text, uncertain=False, condition=''):
    return {'kind': kind, 'text': text + (' 要確認' if uncertain else 'あり') + condition,
            'uncertain': uncertain}


def needs_confirmation(record):
    if record.get('flag'):
        return True
    # An expired absolute application period needs review even if its old status
    # still says 'give'. Relative deadlines (e.g. six months after return) remain
    # eligibility conditions and are not treated as expired.
    text = unicodedata.normalize('NFKC', str(record.get('dl', '')))
    dates = []
    for match in re.finditer(r'(?:令和(\d+)(?:\((\d{4})\))?|(\d{4}))年(\d{1,2})月(\d{1,2})日', text):
        era, western, year, month, day = match.groups()
        try:
            dates.append(date(int(western or year or (2018 + int(era))), int(month), int(day)))
        except ValueError:
            return True
    return bool(dates and max(dates) < date.today() and re.search('まで|期限|終了', text))


def support_labels(return_record, bus_record=None, taxi_record=None):
    result = []
    c, b, t = return_record or {}, bus_record or {}, taxi_record or {}
    programs = b.get('programs', []) if b.get('status') in {'active', 'henno'} else []
    checked_return = any(p.get('kind') == 'henno' and p.get('current') == 'document_checked'
                         for p in programs)
    if c.get('k') in POSITIVE_RETURN:
        # Only this city's benefit record participates: no statewide defaults.
        result.append(label('return', '返納特典', needs_confirmation(c) and not checked_return))
    elif c.get('k') == 'elder' and checked_return:
        result.append(label('return', '返納特典'))
    if programs:
        confirmed = [p for p in programs if p.get('current') == 'document_checked']
        eligible = confirmed or programs
        condition = '（返納が条件）' if all(p.get('kind') == 'henno' for p in eligible) else ''
        result.append(label('bus', 'バス助成', not bool(confirmed), condition))
    elif b.get('status') == 'unknown':
        result.append(label('bus', 'バス助成', True))
    if t.get('k') in POSITIVE_TAXI:
        text = ' '.join(str(t.get(k, '')) for k in ('name', 'what', 'amt'))
        # A ride service with a normal fare is not a subsidy. Use the benefit
        # fields only, so an unrelated subsidy mentioned in notes cannot qualify.
        subsidy = bool(re.search(r'助成|補助|割引|半額|無料|無償|利用券|タクシー券|回数券', text))
        exclusion = bool(re.search(r'(助成|補助|割引).{0,12}(ありません|見つかりません|未確認)', t.get('what', '')))
        if subsidy and (not exclusion or t.get('k') == 'henno_only'):
            condition = {'care': '（要介護等の条件）', 'henno_only': '（返納が条件）'}.get(t['k'], '')
            result.append(label('taxi', 'タクシー助成', needs_confirmation(t), condition))
    return result
