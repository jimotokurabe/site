"""Publish recorded transport supports for the outing worksheet, without entitlement inference.

Only the adopted municipal records are used. A selectable entry is a candidate
for a plan, not a finding that the person qualifies or can travel for free.
"""
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit
import hashlib
import ipaddress
import json
import re

from national_city import LABELS, adopted, gather

FIELD_LABELS = {**LABELS, 'age_min': '記録上の対象年齢の下限'}
FIELDS = ('summary', 'what', 'eligibility', 'age', 'age_min', 'benefit', 'amt', 'fare',
          'routes', 'apply', 'how', 'dl', 'henno_link', 'notes', 'note', 'flag',
          'guide_details', 'guide_relation_note', 'upd', 'updated', 'source_updated')
BLOCKED = {'ended', 'end', 'notfound', 'unknown', 'none', 'needs_confirmation'}
STATE_TEXT = {'ended': '終了の記録あり', 'end': '終了・受付終了の記録あり',
              'notfound': '掲載調査では未確認', 'unknown': '詳細は未確認',
              'none': '支援なしの案内あり', 'needs_confirmation': '現在の条件は要確認'}


def safe_source(url):
    """Only public HTTP(S) source URLs from the curated source fields are exposed."""
    if not isinstance(url, str) or re.search(r'[\s\x00-\x1f\\]', url):
        return False
    try:
        parts = urlsplit(url)
        host = parts.hostname
        if parts.scheme not in ('http', 'https') or not host or parts.username or parts.password:
            return False
        if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')) or '.' not in host:
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return True
    except ValueError:
        return False


def source_rows(record, inherited=''):
    """Retain every explicit source and its own date; never manufacture a URL."""
    candidates = []
    if record.get('url'):
        candidates.append({'url': record['url'], 'label': record.get('src') or record.get('label') or '公式案内',
                           'checked': record.get('checked') or inherited,
                           'updated': record.get('upd') or record.get('updated') or ''})
    for key in ('sources', 'more_sources'):
        rows = record.get(key, [])
        if isinstance(rows, dict):
            rows = [rows]
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, dict):
                candidates.append({'url': row.get('url'), 'label': row.get('label') or row.get('src') or '公式案内',
                                   'checked': row.get('checked') or record.get('checked') or inherited,
                                   'updated': row.get('updated') or row.get('upd') or ''})
    result = []
    for row in candidates:
        if safe_source(row['url']) and row not in result:
            result.append(row)
    return result


def verbatim(value):
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, list):
        return '\n'.join(filter(None, (verbatim(v) for v in value)))
    if isinstance(value, dict):
        return '\n'.join(f'{LABELS.get(k, '補足情報')}：{verbatim(v)}' for k, v in value.items()
                         if verbatim(v) and k not in ('url', 'source'))
    return ''


def detail_rows(record):
    return [{'label': FIELD_LABELS.get(key, '補足・注意'), 'text': verbatim(record[key])}
            for key in FIELDS if key in record and verbatim(record[key])]


def canonical_url(url):
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ''))


def program_id(pid, slug, kind, name, sources):
    identity = [pid, slug, kind, name, sorted({canonical_url(s['url']) for s in sources})]
    digest = hashlib.sha256(json.dumps(identity, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()[:16]
    return f'{kind}-{digest}'


def program(pid, slug, kind, record, inherited, parent=None):
    parent = parent or {}
    checked = record.get('checked') or inherited or ''
    sources = source_rows(record, checked)
    # Municipal bus sources contain conditions not always repeated at program level.
    for source in source_rows(parent, inherited):
        if source not in sources:
            sources.append(source)
    name = record.get('name') or ('バス支援の掲載状況' if kind == 'bus' else 'タクシー支援の掲載状況')
    if name == '記載なし':
        name = 'タクシー支援の掲載状況'
    state = record.get('current') or record.get('status') or record.get('k') or ''
    parent_state = parent.get('status') or ''
    blocked = next((value for value in (parent_state, record.get('status'), record.get('k'), record.get('current'))
                    if value in BLOCKED), '')
    known = state in ('document_checked', 'active') if kind == 'bus' else state in ('yes', 'care', 'henno_only', 'active', 'document_checked')
    selectable = bool(known and not blocked and sources and checked)
    status = STATE_TEXT.get(blocked) or ('掲載記録あり・対象条件を確認' if selectable else '公式出典・現在の条件は要確認')
    details = detail_rows(record)
    for row in detail_rows(parent):
        if row not in details:
            details.append(row)
    anchor = 'support' if kind == 'bus' else 'taxi'
    return {'id': program_id(pid, slug, kind, name, sources), 'name': name,
            'type': kind, 'selectable': selectable, 'status': status, 'checked': checked,
            'sources': sources, 'details': details,
            'page': f'{pid}-menkyo-henno/{slug}.html#{anchor}'}


def catalog(root):
    root = Path(root)
    prefs, bus, taxi, supplements, mobility = gather(root)
    index = {'prefectures': []}
    by_pref = {}
    # Use the same geographic/JIS order as the existing regional picker.
    from build import REGIONS
    order = [pid for _, ids in REGIONS for pid in ids]
    for pid in [pid for pid in order if pid in prefs] + sorted(set(prefs) - set(order)):
        data = prefs[pid]
        pref = {'id': pid, 'name': data['pref']['name'], 'region': next((label for label, ids in REGIONS if pid in ids), 'その他'), 'cities': []}
        cities = []
        for city in data['cities']:
            slug = city['slug']
            a = adopted(pid, city, data, bus, taxi, supplements, mobility)
            programs = []
            if a['bus']:
                record = a['bus']
                entries = record.get('programs') or [dict(record, name='バス支援の掲載状況')]
                for entry in entries:
                    p = program(pid, slug, 'bus', entry, a['bus_checked'], record)
                    if p not in programs:
                        programs.append(p)
            if a['taxi']:
                programs.append(program(pid, slug, 'taxi', a['taxi'], a['taxi_checked']))
            item = {'id': slug, 'name': city['n'], 'kana': city.get('y', ''), 'key': f'{pid}:{slug}',
                    'page': f'{pid}-menkyo-henno/{slug}.html', 'programs': programs}
            city_supplements = []
            for update in a['accepted_supplements']:
                if safe_source(update['source']):
                    city_supplements.append({'label': '確認済みの補足', 'text': verbatim(update['value']),
                                        'source': update['source'],
                                        'checked': update.get('checked') or a['supplement_checked'] or ''})
            if city_supplements:
                item['supplements'] = city_supplements
                unresolved = verbatim(a['supplement_unresolved'])
                if unresolved:
                    item['supplements'].append({'label': 'まだ確認できていないこと', 'text': unresolved,
                                                'source': '', 'checked': a['supplement_checked'] or ''})
            cities.append(item)
            pref['cities'].append({'id': slug, 'name': city['n'], 'kana': city.get('y', '')})
        index['prefectures'].append(pref)
        by_pref[pid] = {'cities': cities}
    return index, by_pref


def write_catalog(root, out):
    """Write beneath the output site's assets directory and return both catalog parts."""
    index, by_pref = catalog(root)
    target = Path(out) / 'assets' / 'outing-supports'
    target.mkdir(parents=True, exist_ok=True)
    for filename, content in [('index', index), *by_pref.items()]:
        (target / f'{filename}.json').write_text(json.dumps(content, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    return index, by_pref


def city_links(soup, pid, slug, city_catalog):
    """Add links only to unambiguous headings; otherwise keep the type unselected."""
    for old in soup.select('[data-outing-support-link]'):
        old.decompose()
    if not city_catalog:
        return soup
    programs = city_catalog.get('programs', [])
    for kind, section_id in [('bus', 'support'), ('taxi', 'taxi')]:
        section = soup.find(id=section_id)
        if section is None:
            continue
        matched = set()
        candidates = [p for p in programs if p['type'] == kind and p['selectable']]
        if kind == 'bus':
            for p in candidates:
                headings = [h for h in section.find_all(['h3', 'h4']) if h.get_text(' ', strip=True) == p['name']
                            and not h.find_parent(class_='archive')]
                same_name = [other for other in candidates if other['name'] == p['name']]
                if len(headings) == 1 and len(same_name) == 1:
                    params = {'pref': pid, 'city': slug, 'support': p['id']}
                    cta = soup.new_tag('a', href='../outing-plan.html?' + urlencode(params))
                    cta['class'] = ['outing-support-cta']
                    cta['data-outing-support-link'] = ''
                    cta.string = 'この支援をお出かけ計画で確認する →'
                    headings[0].insert_after(cta)
                    matched.add(p['id'])
        if kind == 'taxi' and len(candidates) == 1:
            p = candidates[0]
            params = {'pref': pid, 'city': slug, 'support': p['id']}
            cta = soup.new_tag('a', href='../outing-plan.html?' + urlencode(params))
            cta['class'] = ['outing-support-cta']
            cta['data-outing-support-link'] = ''
            cta.string = 'この支援をお出かけ計画で確認する →'
            section.append(cta)
            matched.add(p['id'])
        if not candidates or any(p['id'] not in matched for p in candidates):
            params = {'pref': pid, 'city': slug, 'type': kind}
            cta = soup.new_tag('a', href='../outing-plan.html?' + urlencode(params))
            cta['class'] = ['outing-support-cta']
            cta['data-outing-support-link'] = ''
            cta.string = ('バス' if kind == 'bus' else 'タクシー') + 'と支援をお出かけ計画で確認する →'
            section.append(cta)
    return soup
