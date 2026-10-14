"""Full-rollout assertions and before/after metrics, independent of browser QA."""
import io
import json
import re
import subprocess
import sys
import tarfile
from html.parser import HTMLParser
from pathlib import Path
from bs4 import BeautifulSoup
from national_city import META
from compact_records import EMPTY_VALUES

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT
PHRASES = ['未掲載です', '記載なし', '掲載調査では未確認', '断定するものではありません']


class MainText(HTMLParser):
    def __init__(self):
        super().__init__(); self.inside = False; self.excluded = 0; self.text = []
    def handle_starttag(self, tag, attrs):
        if tag == 'main': self.inside = True
        if tag in ('script', 'style'): self.excluded += 1
    def handle_endtag(self, tag):
        if tag == 'main': self.inside = False
        if tag in ('script', 'style'): self.excluded -= 1
    def handle_data(self, data):
        if self.inside and not self.excluded: self.text.append(data)


def measure(html):
    parser = MainText(); parser.feed(html)
    text = re.sub(r'\s+', '', ''.join(parser.text))
    return {'characters': len(text), **{word: text.count(word) for word in PHRASES}}


def strings(record):
    if isinstance(record, dict):
        for key, value in record.items():
            if key not in META:
                yield from strings(value)
    elif isinstance(record, list):
        for value in record: yield from strings(value)
    elif isinstance(record, str) and record and record not in EMPTY_VALUES:
        yield record


def main():
    paths = json.loads((OUT / 'enriched-pages.json').read_text())
    baseline = subprocess.check_output(['git', 'archive', 'd3a2d002', *paths.values()], cwd=ROOT)
    before = {}
    with tarfile.open(fileobj=io.BytesIO(baseline)) as archive:
        for member in archive:
            if member.isfile(): before[member.name] = measure(archive.extractfile(member).read().decode())
    issues = []; report = {}; source_values = 0
    for pid in sorted({key.split(':')[0] for key in paths}):
        data = json.loads((ROOT / f'data/{pid}-menkyo-henno.json').read_text())
        soup = BeautifulSoup((OUT / f'{pid}-menkyo-henno.html').read_text(), 'html.parser')
        sections = soup.select('#return-procedure')
        if len(sections) != 1:
            issues.append([pid, 'shared procedure count', len(sections)]); continue
        section = sections[0]; text = section.get_text(' ', strip=True)
        hrefs = {a['href'] for a in section.select('a[href]')}
        record = {k: v for k, v in data.get('common', {}).items() if k not in ('tokuten', 'checked')}
        for value in strings(record):
            source_values += 1
            if value not in hrefs and re.sub(r'\s+', ' ', value).strip() not in re.sub(r'\s+', ' ', text).strip():
                issues.append([pid, 'shared procedure record missing', value])
        if record:
            checked = data['common'].get('checked') or data['checked']
            if checked not in text: issues.append([pid, 'shared date missing', checked])
    for key, name in paths.items():
        html = (OUT / name).read_text()
        soup = BeautifulSoup(html, 'html.parser')
        pid = key.split(':')[0]
        entrances = soup.select('.intro .compact-highlight, .intro .overview > li > a')
        if len(entrances) != 4 or {a['href'] for a in entrances} != {'#benefit', '#support', '#taxi', '#rides'}:
            issues.append([key, 'purpose links'])
        if len(soup.select('.intro svg')) != 4: issues.append([key, 'purpose illustrations'])
        if not soup.select_one(f'a[href="../{pid}-menkyo-henno.html#return-procedure"]'):
            issues.append([key, 'missing shared procedure link'])
        if len(soup.select('#family .checklist input')) != 4 or not soup.select_one('[data-share-city]'):
            issues.append([key, 'family controls'])
        if soup.select('.warm-answers, .archive') or '"FAQPage"' in html:
            issues.append([key, 'duplicate archive/FAQ'])
        if soup.select_one('meta[name="robots"][content*="noindex"]'):
            issues.append([key, 'unexpected noindex'])
        report[key] = {'before': before[name], 'after': measure(html)}
    totals = {version: {field: sum(row[version][field] for row in report.values())
                       for field in ['characters', *PHRASES]} for version in ('before', 'after')}
    result = {'baseline_commit': 'd3a2d002', 'cities': len(paths), 'prefectures': 47, 'shared_values_checked': source_values,
              'totals': totals, 'pages': report, 'issues': issues,
              'measurement': 'main text excluding whitespace, includes collapsed text; not an AdSense or user-effect measurement'}
    (ROOT / 'docs/compact-rollout-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != 'pages'}, ensure_ascii=False, indent=2))
    return bool(issues)


if __name__ == '__main__': sys.exit(main())
