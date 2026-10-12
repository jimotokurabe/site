"""Check generated unpublished pilot pages, evidence retention and links."""
import argparse
from collections import Counter
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit
from bs4 import BeautifulSoup
from gomi_integration import city_path
from gomi_pages import _value

ROOT = Path(__file__).resolve().parents[1]


def fact_leaves(value):
    # A rich condition layout may add headings and line breaks; verify every
    # source value survives, rather than requiring the old flattened sentence.
    if isinstance(value, dict):
        return [leaf for child in value.values() for leaf in fact_leaves(child)]
    if isinstance(value, list):
        return [leaf for child in value for leaf in fact_leaves(child)]
    return [_value(value)] if value is not None else []


def check(out, publication=False):
    out = Path(out).resolve()
    data = json.loads((ROOT / 'data/gomi-support.json').read_text())
    errors = []
    paths = ['index.html', 'gomi-support.html', *(city_path(c) for c in data['cities'])]
    parsed = {}
    for relative in paths:
        path = out / relative
        if not path.exists():
            errors.append([relative, 'missing page'])
            continue
        soup = BeautifulSoup(path.read_text(), 'html.parser')
        parsed[relative] = soup
        duplicates = [k for k, v in Counter(n['id'] for n in soup.select('[id]')).items() if v > 1]
        if duplicates:
            errors.append([relative, 'duplicate ids', duplicates])
        if len(soup.select('h1')) != 1:
            errors.append([relative, 'one h1 required'])
        robots = soup.select_one('meta[name="robots"]')
        if not publication and (not robots or 'noindex' not in robots.get('content', '')):
            errors.append([relative, 'draft noindex missing'])
        if publication and robots and 'noindex' in robots.get('content', ''):
            errors.append([relative, 'public page is noindex'])
        for node in soup.select('[href], [src]'):
            href = node.get('href', node.get('src', ''))
            url = urlsplit(href)
            if url.scheme or href.startswith('//'):
                continue
            target = out / unquote(url.path.lstrip('/')) if href.startswith('/') else path.parent / unquote(url.path) if url.path else path
            if target.is_dir():
                target /= 'index.html'
            if not target.exists():
                errors.append([relative, 'missing target', href])
            elif url.fragment and target.suffix == '.html':
                target_soup = soup if target.resolve() == path else BeautifulSoup(target.read_text(), 'html.parser')
                if not target_soup.find(id=unquote(url.fragment)):
                    errors.append([relative, 'missing fragment', href])
        if not publication and relative != 'index.html' and ('googletagmanager' in str(soup) or 'gtag(' in str(soup)):
            errors.append([relative, 'draft contains analytics'])
    retained = 0
    source_map = {s['id']: s for s in data['sources']}
    for city in data['cities']:
        relative = city_path(city)
        soup = parsed.get(relative)
        if soup is None:
            continue
        for service in city['services']:
            route = soup.find(id='route-' + service['id'])
            if route is None:
                errors.append([relative, 'missing route', service['id']])
                continue
            for key, field in service['fields'].items():
                fact = route.select_one(f'[data-field="{key}"]')
                if fact is None:
                    errors.append([relative, 'missing fact', key])
                    continue
                normalized_values = [re.sub(r'\s+', '', leaf) for leaf in fact_leaves(field['value'])]
                normalized_fact = re.sub(r'\s+', '', fact.get_text(' ', strip=True))
                if any(value not in normalized_fact for value in normalized_values):
                    errors.append([relative, 'fact value lost', service['id'], key])
                retained += 1
                for sid in field['source_ids']:
                    if not route.find('a', href=source_map[sid]['url']):
                        errors.append([relative, 'source lost', sid])
                    if source_map[sid]['checked'] not in route.get_text():
                        errors.append([relative, 'source date lost', sid])
        questions = city.get('common_questions_for_office', []) + [q for service in city['services'] for q in service.get('questions_for_office', [])]
        for question in questions:
            if question not in soup.get_text():
                errors.append([relative, 'question lost', question])
        mobility = BeautifulSoup((out / city['id'].replace(':', '-menkyo-henno/')).with_suffix('.html').read_text(), 'html.parser')
        if not mobility.find('a', href='../' + relative):
            errors.append([relative, 'missing related link'])
    if not publication and 'Disallow: /' not in (out / 'robots.txt').read_text():
        errors.append(['robots.txt', 'draft must be blocked'])
    if not publication and '<loc>' in (out / 'sitemap.xml').read_text():
        errors.append(['sitemap.xml', 'draft URLs exposed'])
    if publication:
        sitemap = (out / 'sitemap.xml').read_text()
        for relative in paths[1:]:
            if 'https://jimotokurabe.jp/' + relative not in sitemap:
                errors.append([relative, 'missing public sitemap entry'])
    return {'new_pages': len(paths) - 1, 'retained_fields': retained, 'issues': errors}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('--publication', action='store_true')
    args = parser.parse_args()
    result = check(args.out, publication=args.publication)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(bool(result['issues']))
