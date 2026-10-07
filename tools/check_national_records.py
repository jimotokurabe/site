"""Read-only check that national municipality pages retain local source records.

Checks rendered body text (including expandable details), excluding scripts/styles.
No embedded management archive is needed or treated as evidence of retention.
"""
from collections import defaultdict
from pathlib import Path
import json
import re
import sys
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT
requirements = defaultdict(lambda: {'texts': set(), 'urls': set(), 'dates': set()})
issues = []


class BodyRecords(HTMLParser):
    """Collect only human-readable body text and its links in one streaming pass."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_body = False
        self.excluded = 0
        self.text = []
        self.hrefs = set()

    def handle_starttag(self, tag, attrs):
        if tag == 'body':
            self.in_body = True
        if tag in {'script', 'style'}:
            self.excluded += 1
        if self.in_body and not self.excluded and tag == 'a':
            self.hrefs.add(dict(attrs).get('href'))

    def handle_endtag(self, tag):
        if tag in {'script', 'style'}:
            self.excluded = max(0, self.excluded - 1)
        if tag == 'body':
            self.in_body = False

    def handle_data(self, data):
        if self.in_body and not self.excluded:
            self.text.append(data.strip())


def norm(value):
    return re.sub(r'\s+', ' ', str(value)).strip()


def scalars(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from scalars(v)
    elif isinstance(value, list):
        for v in value:
            yield from scalars(v)
    elif isinstance(value, str) and value.strip():
        yield value


def collect(record, required, inherited='', category='', trail=''):
    if isinstance(record, dict):
        checked = record.get('checked') or inherited
        if checked:
            required['dates'].add(str(checked))
        for field, value in record.items():
            label = category + ' ' + trail + field
            # Substantive conditions and warnings must remain in readable text.
            if field in {'what', 'note', 'notes', 'flag', 'henno_link', 'eligibility', 'benefit', 'fare', 'routes', 'apply', 'cautions', 'unresolved'}:
                for item in scalars(value):
                    if not item.startswith(('https://', 'http://')):
                        required['texts'].add((label, norm(item)))
            collect(value, required, checked, category, trail + field + '.')
    elif isinstance(record, list):
        for item in record:
            collect(item, required, inherited, category, trail)
    elif isinstance(record, str) and re.fullmatch(r'https?://\S+', record):
        required['urls'].add(record)


for suffix, category in [('menkyo-henno', '返納'), ('bus', 'バス'), ('taxi', 'タクシー')]:
    for path in sorted((ROOT / 'data').glob('*-' + suffix + '.json')):
        data = json.loads(path.read_text())
        pref = path.name.removesuffix('-' + suffix + '.json')
        cities = data.get('cities', [])
        entries = cities.items() if isinstance(cities, dict) else ((c['slug'], c) for c in cities)
        for slug, city in entries:
            collect(city, requirements[pref + ':' + slug], data.get('checked', ''), category)

manifest = json.loads((ROOT / 'data/municipality-supplements.json').read_text())['municipalities']
keys = {row['key'] for row in manifest}
prefs = {key.split(':')[0] for key in keys}
if len(keys) != 1741 or len(prefs) != 47:
    issues.append(['manifest', 'expected 1741 unique municipalities and 47 prefectures', len(keys), len(prefs)])
checks = {'texts': 0, 'urls': 0, 'dates': 0}
for key in sorted(keys):
    pref, slug = key.split(':', 1)
    path = OUT / f'{pref}-menkyo-henno/{slug}.html'
    if not path.is_file():
        issues.append([key, 'missing page'])
        continue
    body = BodyRecords()
    body.feed(path.read_text())
    visible = norm(' '.join(body.text))
    hrefs = body.hrefs
    required = requirements[key]
    for label, value in sorted(required['texts']):
        checks['texts'] += 1
        if value not in visible:
            issues.append([key, 'record text missing', label, value[:200]])
    for url in sorted(required['urls']):
        checks['urls'] += 1
        if url not in hrefs:
            issues.append([key, 'source URL missing', url])
    for date in sorted(required['dates']):
        checks['dates'] += 1
        alternatives = [date]
        match = re.fullmatch(r'(20\d\d)-(\d\d)-(\d\d)', date)
        if match:
            alternatives.append(f'{int(match[1])}年{int(match[2])}月{int(match[3])}日')
        if not any(candidate in visible for candidate in alternatives):
            issues.append([key, 'confirmation date missing', date])
print(json.dumps({'municipalities': len(keys), 'prefectures': len(prefs), 'checks': checks, 'issues': issues}, ensure_ascii=False, indent=2))
sys.exit(bool(issues))
