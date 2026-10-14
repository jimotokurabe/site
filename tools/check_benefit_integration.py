"""Check nationwide benefit integration against the unmodified Git baseline.

Usage: python tools/check_benefit_integration.py [generated-site-root]
The baseline defaults to 8765f097; override it with BENEFIT_BASELINE when
a different reviewed commit is required.
"""
from collections import Counter
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import io

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT
BASELINE = os.environ.get('BENEFIT_BASELINE', '8765f0971b5b6584ff0fc2e010db1d378af354e3')
ITEMS = ('benefit', 'support', 'taxi', 'rides')
issues = []


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def norm(value):
    return re.sub(r'\s+', ' ', value).strip()


def baseline_files(paths):
    """Read only the manifest, data JSON inventory, and relevant city pages."""
    archive = git('archive', '--format=tar', BASELINE, *paths)
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as tar:
        return {member.name: tar.extractfile(member).read()
                for member in tar if member.isfile()}


def dates(text):
    return Counter(re.findall(r'20\d{2}(?:-\d{2}-\d{2}|年\d{1,2}月\d{1,2}日)', text))


def check_data_unchanged(baseline):
    base_names = {name for name in baseline if name.startswith('data/') and name.endswith('.json')}
    now_names = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'data').rglob('*.json')}
    for name in sorted(base_names | now_names):
        before = baseline.get(name)
        path = ROOT / name
        after = path.read_bytes() if path.is_file() else None
        if before != after:
            issues.append([name, 'data JSON changed from baseline'])


def main():
    try:
        manifest_bytes = git('show', f'{BASELINE}:data/municipality-supplements.json')
        manifest = json.loads(manifest_bytes)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f'Cannot read baseline {BASELINE}: {exc}', file=sys.stderr)
        return 2

    rows = manifest.get('municipalities', [])
    keys = [row.get('key', '') for row in rows]
    if len(keys) != 1741 or len(set(keys)) != 1741:
        issues.append(['manifest', 'expected 1741 unique municipality keys', len(keys), len(set(keys))])
    prefectures = {key.split(':', 1)[0] for key in keys if ':' in key}
    if len(prefectures) != 47:
        issues.append(['manifest', 'expected 47 prefectures', len(prefectures)])
    page_paths = [f'{key.split(":", 1)[0]}-menkyo-henno/{key.split(":", 1)[1]}.html'
                  for key in keys if ':' in key]
    tracked_data = [p.decode() for p in git('ls-tree', '-r', '--name-only', BASELINE, '--', 'data').splitlines()
                    if p.decode().endswith('.json')]
    baseline = baseline_files(tracked_data + page_paths)
    check_data_unchanged(baseline)

    checks = Counter()
    baseline_nested_records = Counter()
    for key, relpath in zip(keys, page_paths):
        pref, slug = key.split(':', 1)
        original_html = baseline.get(relpath)
        output_path = OUT / relpath
        if original_html is None:
            issues.append([key, 'baseline page missing'])
            continue
        if not output_path.is_file():
            issues.append([key, 'generated page missing'])
            continue
        before = BeautifulSoup(original_html, 'html.parser')
        after = BeautifulSoup(output_path.read_text(encoding='utf-8'), 'html.parser')

        entrances = after.select('#benefit-browser .benefit-list a.benefit-card[href]')
        entrance_map = Counter(a.get('href') for a in entrances)
        if entrance_map != Counter('#' + item for item in ITEMS) or len(entrances) != 4:
            issues.append([key, 'expected exactly four benefit entrances', dict(entrance_map)])
        if len(after.select('#benefit-browser .original-record')) != 4:
            issues.append([key, 'expected all four original records inside benefit browser'])
        for item in ITEMS:
            card = after.select(f'#benefit-browser a[data-pick="{item}"]')
            panel = after.select(f'#benefit-browser .integrated-panel#{item}')
            record = after.select(f'#record-{item}.original-record')
            baseline_record = before.select(f'#{item}')
            if len(card) != 1 or card[0].get('aria-controls') != item:
                issues.append([key, item, 'entrance control missing or ambiguous'])
            if len(panel) != 1 or len(record) != 1 or len(baseline_record) != 1:
                issues.append([key, item, 'record/panel ID missing or ambiguous'])
                continue
            if record[0].find_parent(class_='integrated-panel') is not panel[0]:
                issues.append([key, item, 'original record is outside its matching panel'])

            old = baseline_record[0]
            new = record[0]
            # Historical Yokohama markup nests the return-benefit section in
            # the bus section. The transform extracts each ID once, so compare
            # each baseline section's exclusive contents and audit nested IDs
            # independently against their own generated record below.
            exclusive_old = copy.deepcopy(old)
            for nested_item in ITEMS:
                if nested_item == item:
                    continue
                nested = exclusive_old.select(f'#{nested_item}')
                if nested:
                    baseline_nested_records[f'{item}>{nested_item}'] += len(nested)
                    for node in nested:
                        node.decompose()
            unexpected_nested = [node.get('id') for node in new.select('[id]')
                                 if node.get('id') in ITEMS and node.get('id') != item]
            if unexpected_nested:
                issues.append([key, item, 'generated record still nests another record ID', unexpected_nested])
            old_text = norm(exclusive_old.get_text(' ', strip=True))
            new_text = norm(new.get_text(' ', strip=True))
            checks['record_texts'] += 1
            if old_text != new_text:
                issues.append([key, item, 'original record text changed'])
            old_urls = Counter(a.get('href') for a in exclusive_old.select('a[href]'))
            new_urls = Counter(a.get('href') for a in new.select('a[href]'))
            checks['source_url_sets'] += 1
            if old_urls != new_urls:
                issues.append([key, item, 'original record source URLs changed',
                               'missing=' + repr(list((old_urls - new_urls).elements())[:4]),
                               'added=' + repr(list((new_urls - old_urls).elements())[:4])])
            if dates(old_text) != dates(new_text):
                issues.append([key, item, 'original record dates changed'])
            checks['record_dates'] += sum(dates(old_text).values())

            actions = panel[0].select(f'.family-actions [data-add-family="{item}"]')
            family_links = panel[0].select('.family-actions a[href="#family"]')
            if len(actions) != 1 or len(family_links) != 1:
                issues.append([key, item, 'family memo/action link missing'])

        procedure = f'../{pref}-menkyo-henno.html#return-procedure'
        if not after.select_one(f'a[href="{procedure}"]'):
            issues.append([key, 'shared procedure link missing'])
        if len(after.select('#family .checklist input')) != 4 or not after.select_one('#family [data-share-city]'):
            issues.append([key, 'family checklist/share controls missing'])
        checks['municipalities'] += 1

    result = {'baseline': BASELINE, 'municipalities': checks['municipalities'],
              'prefectures': len(prefectures), 'checks': dict(checks),
              'baseline_nested_record_ids': dict(baseline_nested_records), 'issues': issues}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return bool(issues)


if __name__ == '__main__':
    sys.exit(main())
