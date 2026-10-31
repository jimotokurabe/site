"""Check that transport-cost navigation keeps existing national records intact.

Usage: python tools/check_transport_cost_preservation.py [generated-site-root]
The reviewed baseline defaults to fafc5001. Set TRANSPORT_BASELINE to override.
"""
from collections import Counter
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT
BASELINE = os.environ.get('TRANSPORT_BASELINE', 'fafc5001c570dc9e2bd6a39258995029783d69a3')
issues = []


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def baseline_files(paths):
    archive = git('archive', '--format=tar', BASELINE, *paths)
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as tar:
        return {member.name: tar.extractfile(member).read()
                for member in tar if member.isfile()}


def read_manifest():
    raw = git('show', f'{BASELINE}:data/municipality-supplements.json')
    return json.loads(raw)


def strip_new_transport_links(soup):
    """Ignore the calculator/planner entrance while preserving all old records."""
    for entrance in soup.select('.transport-cost-link'):
        entrance.decompose()
    for link in soup.select('a[href]'):
        path = urlsplit(link.get('href', '')).path.rstrip('/')
        if path.endswith('/transport-cost.html') or path == 'transport-cost.html':
            link.decompose()


def visible_text(raw):
    soup = BeautifulSoup(raw, 'html.parser')
    strip_new_transport_links(soup)
    body = soup.body or soup
    for node in body.select('script, style, noscript, template'):
        node.decompose()
    return re.sub(r'\s+', ' ', body.get_text(' ', strip=True)).strip()


def page_links(raw):
    soup = BeautifulSoup(raw, 'html.parser')
    strip_new_transport_links(soup)
    return Counter(a.get('href') for a in soup.select('a[href]'))


def family_signature(raw):
    soup = BeautifulSoup(raw, 'html.parser')
    strip_new_transport_links(soup)
    family = soup.select_one('#family')
    if family is None:
        return None

    def shape(node):
        if isinstance(node, NavigableString):
            text = re.sub(r'\s+', ' ', str(node)).strip()
            return ('text', text) if text else None
        if not isinstance(node, Tag):
            return None
        attrs = tuple(sorted((key, tuple(value) if isinstance(value, list) else str(value))
                             for key, value in node.attrs.items()))
        children = tuple(item for child in node.children
                         if (item := shape(child)) is not None)
        return (node.name, attrs, children)

    return shape(family)


def main():
    try:
        rows = read_manifest().get('municipalities', [])
        keys = [row.get('key', '') for row in rows]
        if len(keys) != 1741 or len(set(keys)) != 1741:
            issues.append(['baseline manifest', 'expected 1741 unique municipality keys', len(keys), len(set(keys))])
        page_paths = [f'{key.split(":", 1)[0]}-menkyo-henno/{key.split(":", 1)[1]}.html'
                      for key in keys if ':' in key]
        tracked = [name.decode() for name in git('ls-tree', '-r', '--name-only', BASELINE,
                                                  '--', 'data', 'assets/outing-supports').splitlines()
                   if name.decode().endswith('.json')]
        baseline = baseline_files(tracked + page_paths)
    except (subprocess.CalledProcessError, json.JSONDecodeError, IndexError) as exc:
        print(f'Cannot read baseline {BASELINE}: {exc}', file=sys.stderr)
        return 2

    source_data = [name for name in tracked if name.startswith('data/')]
    outing_data = [name for name in tracked if name.startswith('assets/outing-supports/')]
    checks = Counter()
    now_source = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'data').rglob('*.json')} - {'data/transport-estimate-verified.json', 'data/transport-estimate-reviewed.json'}
    now_outing = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'assets/outing-supports').glob('*.json')}
    for name in sorted(set(source_data) | now_source | set(outing_data) | now_outing):
        before = baseline.get(name)
        path = ROOT / name
        after = path.read_bytes() if path.is_file() else None
        if before != after:
            issues.append([name, 'baseline source JSON missing or changed'])
        elif name.startswith('data/'):
            checks['source_json_files'] += 1
        else:
            checks['outing_json_files'] += 1
    if len(outing_data) != 48:
        issues.append(['outing-supports', 'expected 47 prefecture files plus index', len(outing_data)])

    prefectures = {key.split(':', 1)[0] for key in keys if ':' in key}
    if len(prefectures) != 47:
        issues.append(['baseline manifest', 'expected 47 prefectures', len(prefectures)])
    for key, relpath in zip(keys, page_paths):
        before = baseline.get(relpath)
        output = OUT / relpath
        if before is None:
            issues.append([key, 'baseline municipality page missing'])
            continue
        if not output.is_file():
            issues.append([key, 'municipality page missing after build'])
            continue
        after = output.read_bytes()
        checks['municipality_pages'] += 1
        if visible_text(before) != visible_text(after):
            issues.append([key, 'existing visible text, including source details or confirmation dates, changed'])
        checks['visible_page_texts'] += 1
        if page_links(before) != page_links(after):
            issues.append([key, 'existing page links or source URLs changed'])
        checks['page_link_sets'] += 1
        if family_signature(before) != family_signature(after):
            issues.append([key, 'family sharing UI changed or disappeared'])
        checks['family_ui'] += 1

    result = {'baseline': BASELINE, 'municipalities': checks['municipality_pages'],
              'prefectures': len(prefectures), 'checks': dict(checks), 'issues': issues}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return bool(issues)


if __name__ == '__main__':
    sys.exit(main())
