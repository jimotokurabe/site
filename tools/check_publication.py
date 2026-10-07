"""Verify nationwide public metadata, navigation and local references."""
from pathlib import Path
from urllib.parse import urlsplit, unquote
from collections import Counter
import json
import re
import sys
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT
BASE = 'https://jimotokurabe.jp/'
GA = 'G-T1PQ72Q40S'
ADS = 'ca-pub-2542211932832864'
paths = json.loads((OUT / 'enriched-pages.json').read_text())
issues, page_info, local_links = [], {}, []


def resolve(source, value):
    u = urlsplit(value)
    if u.scheme or value.startswith('//'):
        return None
    target = OUT / unquote(u.path.lstrip('/')) if u.path.startswith('/') else source.parent / unquote(u.path) if u.path else source
    if target.is_dir():
        target /= 'index.html'
    return target.resolve(), unquote(u.fragment)


for f in sorted(OUT.rglob('*.html')):
    rel = f.relative_to(OUT)
    if any(part in {'.git', 'preview', 'node_modules'} for part in rel.parts):
        continue
    raw = f.read_text()
    s = BeautifulSoup(raw, 'html.parser')
    ids = [e['id'] for e in s.select('[id]')]
    duplicate_ids = [i for i, n in Counter(ids).items() if n > 1]
    if duplicate_ids:
        issues.append([str(rel), 'duplicate ids', duplicate_ids])
    canonical = s.select_one('link[rel="canonical"]')
    canonical = canonical.get('href') if canonical else None
    expected = BASE + ('' if str(rel) == 'index.html' else rel.as_posix())
    if canonical != expected:
        issues.append([str(rel), 'canonical', canonical, expected])
    if len(s.select('h1')) != 1:
        issues.append([str(rel), 'h1 count'])
    robots = [m.get('content', '').lower() for m in s.select('meta[name="robots"],meta[name="googlebot"]')]
    if any('noindex' in r or 'nofollow' in r for r in robots):
        issues.append([str(rel), 'public robots'])
    if not s.select_one('script[src="https://www.googletagmanager.com/gtag/js?id=' + GA + '"]') or not re.search(r"gtag\(\s*['\"]config['\"]\s*,\s*['\"]" + GA, raw):
        issues.append([str(rel), 'analytics'])
    ad = s.select_one('meta[name="google-adsense-account"]')
    if not ad or ad.get('content') != ADS:
        issues.append([str(rel), 'adsense account'])
    for field in ('type', 'site_name', 'title', 'description', 'url', 'locale'):
        meta = s.select_one('meta[property="og:' + field + '"]')
        if not meta or not meta.get('content') or (field == 'url' and meta['content'] != expected):
            issues.append([str(rel), 'og:' + field])
    visible = ' '.join(str(t).strip() for t in s.find_all(string=True) if not any(p.name in {'script', 'style'} for p in t.parents))
    if re.search(r'未公開|プレビュー|画面構成の確認用', visible) or s.select_one('.draft,.draftbar,#preserved-records'):
        issues.append([str(rel), 'unpublished content/archive'])
    href_targets = {target[0] for a in s.select('a[href]') if (target := resolve(f, a['href']))}
    footer = s.select_one('footer')
    footer_targets = {target[0] for a in footer.select('a[href]') if (target := resolve(f, a['href']))} if footer else set()
    if not footer or not {(OUT / name).resolve() for name in ('about.html', 'privacy.html')} <= footer_targets:
        issues.append([str(rel), 'footer legal links'])
    crumb = s.select_one('.crumb,.crumbs')
    crumb_targets = {target[0] for a in crumb.select('a[href]') if (target := resolve(f, a['href']))} if crumb else set()
    page_info[f.resolve()] = {'ids': set(ids) | {a['name'] for a in s.select('a[name]')}, 'canonical': canonical, 'targets': href_targets, 'crumb': crumb_targets}
    for a in s.select('[href],[src]'):
        href = a.get('href', a.get('src', ''))
        target = resolve(f, href)
        if target:
            local_links.append((f.resolve(), *target, href))

for f, target, fragment, href in local_links:
    if not target.exists():
        issues.append([str(f.relative_to(OUT)), 'missing local target', href])
    elif fragment and target.suffix == '.html' and (target not in page_info or fragment not in page_info[target]['ids']):
        issues.append([str(f.relative_to(OUT)), 'missing anchor', href])

home = (OUT / 'index.html').read_text()
match = re.search(r'const\s+cities\s*=\s*', home)
try:
    cities = json.JSONDecoder().raw_decode(home[match.end():])[0] if match else []
except ValueError:
    cities = []
if len(paths) != 1741 or len(cities) != 1741 or {c.get('url') for c in cities} != set(paths.values()):
    issues.append(['index.html', 'municipality search manifest', len(paths), len(cities)])
prefectures = {k.split(':')[0] for k in paths}
if len(prefectures) != 47:
    issues.append(['manifest', 'prefecture count', len(prefectures)])
sitemap_list = [n.text for n in ET.parse(OUT / 'sitemap.xml').findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
sitemap = set(sitemap_list)
if len(sitemap_list) != len(sitemap):
    issues.append(['sitemap.xml', 'duplicate URLs'])
public_canonicals = {p['canonical'] for p in page_info.values() if p['canonical']}
if sitemap != public_canonicals:
    issues.append(['sitemap.xml', 'public canonical coverage', sorted(public_canonicals - sitemap), sorted(sitemap - public_canonicals)])
for key, path in paths.items():
    f = (OUT / path).resolve()
    pref = (OUT / (key.split(':')[0] + '-menkyo-henno.html')).resolve()
    p = page_info.get(f)
    if not p:
        issues.append([key, 'missing municipality page'])
        continue
    if p['canonical'] not in sitemap:
        issues.append([key, 'sitemap'])
    if not {pref, (OUT / 'index.html').resolve()} <= p['crumb']:
        issues.append([key, 'breadcrumb'])
    if f not in page_info.get(pref, {}).get('targets', set()):
        issues.append([key, 'prefecture navigation'])
for pid in sorted(prefectures):
    pref = (OUT / (pid + '-menkyo-henno.html')).resolve()
    if pref not in page_info.get((OUT / 'index.html').resolve(), {}).get('targets', set()):
        issues.append([pid, 'top prefecture navigation'])
    if BASE + pref.name not in sitemap:
        issues.append([pid, 'prefecture sitemap'])
if BASE not in sitemap:
    issues.append(['index.html', 'sitemap'])
if (OUT / 'CNAME').read_text().strip() != 'jimotokurabe.jp' or not (OUT / '.nojekyll').exists():
    issues.append(['hosting configuration'])
robots = (OUT / 'robots.txt').read_text()
if 'Allow: /' not in robots or 'Disallow: /\n' in robots or BASE + 'sitemap.xml' not in robots:
    issues.append(['robots.txt', 'public indexing configuration'])
print(json.dumps({'municipalities': len(paths), 'prefectures': len(prefectures), 'public_html_pages': len(page_info), 'sitemap_urls': len(sitemap), 'issues': issues}, ensure_ascii=False, indent=2))
sys.exit(bool(issues))
