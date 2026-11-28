"""Verify nationwide public metadata, navigation and local references."""
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote
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
redirects = json.loads((ROOT / 'tools' / 'mobility-redirects.json').read_text())
redirect_files = set()
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
    if rel.as_posix() in redirects:
        redirect_files.add(rel.as_posix())
        destination = redirects[rel.as_posix()]
        redirect_link = BASE + destination + '#rides'
        meta = s.select('meta[http-equiv="refresh"]')
        refresh = meta[0].get('content', '').split('; url=', 1) if len(meta) == 1 else []
        manual = s.select('a[href]')
        if (len(refresh) != 2 or refresh[0] != '0'
                or urljoin(expected, refresh[1]) != redirect_link):
            issues.append([str(rel), 'invalid redirect refresh', refresh, redirect_link])
        if (len(manual) != 1 or urljoin(expected, manual[0]['href']) != redirect_link
                or s.body is None or s.body.get_text(strip=True) != manual[0].get_text(strip=True)):
            issues.append([str(rel), 'invalid manual redirect link', redirect_link])
        if canonical != BASE + destination or len(s.select('link[rel="canonical"]')) != 1:
            issues.append([str(rel), 'invalid redirect canonical', canonical, destination])
        if s.select('script, iframe, img, style, link[rel="stylesheet"], meta[name="robots"], meta[name="googlebot"]'):
            issues.append([str(rel), 'redirect has scripts, assets or robots directives'])
        continue
    if '-mobility/' in rel.as_posix() or s.select_one('meta[http-equiv="refresh"]'):
        issues.append([str(rel), 'unexpected redirect'])
    if canonical != expected:
        issues.append([str(rel), 'canonical', canonical, expected])
    if len(s.select('h1')) != 1:
        issues.append([str(rel), 'h1 count'])
    robots = [m.get('content', '').lower() for m in s.select('meta[name="robots"],meta[name="googlebot"]')]
    if any('noindex' in r or 'nofollow' in r for r in robots):
        issues.append([str(rel), 'public robots'])
    trackers = s.select('script[data-jk-analytics="gtag"]')
    if len(trackers) != 1 or 'assets/analytics.js?v=' not in trackers[0].get('src', '') or 'googletagmanager.com/gtag/js' in raw:
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
        absolute = urlsplit(urljoin(expected, href))
        if absolute.netloc == urlsplit(BASE).netloc and unquote(absolute.path.lstrip('/')) in redirects:
            issues.append([str(rel), 'link to old mobility URL', href])
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
for old in sorted(set(redirects) - redirect_files):
    issues.append([old, 'missing mobility redirect'])
for old, destination in redirects.items():
    page = page_info.get((OUT / destination).resolve())
    if destination not in paths.values() or not page or 'rides' not in page['ids']:
        issues.append([old, 'missing municipality or mobility section', destination])
    if BASE + old in sitemap:
        issues.append([old, 'redirect in sitemap'])
search_data = json.loads((OUT / 'mobility-city-index.json').read_text())
for row in search_data['cities']:
    for detail in row['details']:
        if detail['url'] != paths.get(row['key'], '') + '#rides':
            issues.append([row['key'], 'mobility search points outside municipality section', detail['url']])
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
print(json.dumps({'municipalities': len(paths), 'prefectures': len(prefectures), 'public_html_pages': len(page_info) + len(redirect_files), 'mobility_redirects': len(redirect_files), 'sitemap_urls': len(sitemap), 'issues': issues}, ensure_ascii=False, indent=2))
sys.exit(bool(issues))
