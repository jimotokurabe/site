"""Publish the municipality-first navigation using local, audited source data."""
from pathlib import Path
import copy
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import build as b
from site_header import apply_site_header
from seo_markup import apply as apply_seo_markup

SIBLINGS_EACH_SIDE = 4


def pref_orders(paths):
    """県ごとの市町村の並び（各県の返納データの順）。公開ページがあるものだけ。"""
    orders = {}
    for key in paths:
        pid = key.split(':')[0]
        if pid in orders:
            continue
        data = json.loads((b.ROOT/f'data/{pid}-menkyo-henno.json').read_text(encoding='utf-8'))
        orders[pid] = (data['pref'], [(c['slug'], c['n']) for c in data['cities']
                                      if f"{pid}:{c['slug']}" in paths])
    return orders


def siblings_section(soup, relative, orders):
    """同じ県のほかの市町村へのリンク。隣接は確かめていないので「近く」とは書かない。"""
    if '-menkyo-henno/' not in relative:
        return
    pid, slug = relative.split('-menkyo-henno/')
    slug = slug.removesuffix('.html')
    pref, cities = orders.get(pid, (None, []))
    slugs = [c[0] for c in cities]
    if slug not in slugs or len(cities) < 2:
        return
    i = slugs.index(slug)
    n = len(cities)
    picks = []
    for offset in range(1, SIBLINGS_EACH_SIDE + 1):
        for j in (i - offset, i + offset):
            c = cities[j % n]
            if c[0] != slug and c not in picks:
                picks.append(c)
    picks = picks[:SIBLINGS_EACH_SIDE * 2] if n > SIBLINGS_EACH_SIDE * 2 else [c for c in cities if c[0] != slug]
    picks.sort(key=lambda c: slugs.index(c[0]))
    unit = pref.get('unit', '市町村')
    html = (f'<section class="block siblings" id="siblings" aria-labelledby="siblings-title">'
            f'<h2 id="siblings-title">{b.e(pref["name"])}のほかの{b.e(unit)}</h2>'
            f'<p class="note">制度は{b.e(unit)}ごとにちがいます。同じ{b.e(pref["name"])}のページを続けて確認できます。</p>'
            '<ul>' + ''.join(f'<li><a href="{b.e(s)}.html">{b.e(name)}</a></li>' for s, name in picks) + '</ul>'
            f'<p><a class="all" href="../{pid}-menkyo-henno.html">{b.e(pref["name"])}の{b.e(unit)}の一覧へ</a></p></section>')
    for old in soup.select('#siblings'):
        old.decompose()
    target = soup.select_one('.content') or soup.main
    if target is not None:
        target.append(BeautifulSoup(html, 'html.parser'))


def finalize(path, relative, legacy_ids, draft, orders=None):
    soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
    base = '../' if '/' in relative else ''
    description = soup.select_one('meta[name="description"]')['content']
    canonical_path = '' if relative == 'index.html' else relative
    shell = BeautifulSoup(b.shell(title=soup.title.get_text(), description=description,
                                 path=canonical_path, main='', draft=draft, base=base), 'html.parser')
    for node in soup.select('meta[name="robots"], meta[name="referrer"], link[rel="canonical"], meta[property^="og:"], meta[name="google-adsense-account"]'):
        node.decompose()
    for node in shell.head.select('meta[name="robots"], link[rel="canonical"], meta[property^="og:"], meta[name="google-adsense-account"]'):
        soup.head.append(copy.copy(node))
    if not draft:
        for script in shell.head.find_all('script'):
            if 'gtag' in str(script) or 'googletagmanager' in str(script):
                node = copy.copy(script)
                soup.head.append(node)
    for banner in soup.select('.draft, .draftbar'):
        if draft:
            banner.string = 'これは公開前の下書きです。制度の確認日は各出典に記載しています。'
        else:
            banner.decompose()
    for node in soup.select('#preserved-records'):
        node.decompose()
    # Reference links remain usable, but links to this same public page do not
    # need a misleading "currently published" label after the redesign ships.
    for link in list(soup.select('a[href]')):
        if link.get('href') == b.SITE + relative and '公開' in link.get_text():
            link.decompose()
    for paragraph in list(soup.find_all('p')):
        if paragraph.get_text(strip=True) == 'この2つのリンクは、現在の公開ページを開きます。':
            paragraph.decompose()
    footer = soup.find('footer')
    if footer:
        footer.append(copy.copy(shell.footer.nav))
        footer.append(copy.copy(shell.footer.find('p')))
    # 「ほかの市町村」は、古い id の照合より前に足す（照合後に足すと id が二重になる）
    siblings_section(soup, relative, orders or {})
    # Keep pre-existing deep links working when sections move into city pages.
    ids = {node['id'] for node in soup.select('[id]')}
    for old_id in sorted(legacy_ids - ids):
        target = soup.select_one('#procedure') if old_id.startswith('step-') else None
        target = target or soup.select_one('#support') if old_id == 'bus' else target
        if target is None and relative.count('/') == 0 and relative != 'index.html':
            slug = old_id.removeprefix('city-').removeprefix('c-')
            link = soup.find('a', href=lambda href: bool(href and href.endswith('/' + slug + '.html')))
            target = link.parent if link else None
        target = target or soup.main
        alias = soup.new_tag('span', id=old_id, attrs={'class':'legacy-anchor','aria-hidden':'true'})
        target.insert(0, alias)
    if not draft:
        for button in soup.select('button.print'):
            button['data-print'] = ''
        related = soup.select_one('#related')
        if related:
            related['data-related-support'] = ''
        soup.body.append(BeautifulSoup(b.ACTION_SCRIPT, 'html.parser'))
    apply_site_header(soup, base=base, home=relative == 'index.html')
    if relative == 'index.html':
        from colorful_home import apply_colorful_home
        apply_colorful_home(soup)
    apply_seo_markup(soup, relative)
    path.write_text(str(soup), encoding='utf-8')


def render(out, draft=False):
    out = Path(out)
    import shutil
    (out/'assets').mkdir(exist_ok=True)
    for name in ('site-header.css', 'site-header.js', 'colorful-home.css', 'family-home-color.webp', 'town-mobility-home.webp'):
        if (b.ROOT/'assets'/name).resolve() != (out/'assets'/name).resolve():
            shutil.copy2(b.ROOT/'assets'/name, out/'assets'/name)
    dataset = json.loads((b.ROOT/'data/municipality-supplements.json').read_text())
    paths = {row['key']:row['key'].replace(':', '-menkyo-henno/')+'.html' for row in dataset['municipalities']}
    targets = ['index.html', *sorted({key.split(':')[0]+'-menkyo-henno.html' for key in paths}), *paths.values()]
    old_ids = {}
    for relative in targets:
        path = out/relative
        old_ids[relative] = {node['id'] for node in BeautifulSoup(path.read_text(), 'html.parser').select('[id]')} if path.exists() else set()
    subprocess.run([sys.executable, str(b.ROOT/'tools/national_navigation.py'), '--root', str(b.ROOT), '--out', str(out)], check=True)
    from national_city import build_all
    result = build_all(b.ROOT, out, draft=draft)
    orders = pref_orders(paths)
    for relative in targets:
        finalize(out/relative, relative, old_ids[relative], draft, orders)
    (out/'enriched-pages.json').write_text(json.dumps(paths, ensure_ascii=False, indent=2), encoding='utf-8')
    if not draft:
        ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
        ET.register_namespace('', ns)
        tree = ET.parse(out/'sitemap.xml')
        existing = {el.text for el in tree.findall('.//{'+ns+'}loc')}
        for path in paths.values():
            if b.SITE+path not in existing:
                node = ET.SubElement(tree.getroot(), '{'+ns+'}url')
                ET.SubElement(node, '{'+ns+'}loc').text = b.SITE+path
        tree.write(out/'sitemap.xml', encoding='utf-8', xml_declaration=True)
    print('built nationwide support pages:', len(paths), '| draft' if draft else '| public')
    return result
