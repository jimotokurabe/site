"""Opt-in unpublished waste pilot; reviewed data can later use the public build."""
import json
from html import escape
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup


def prepare(root, out, *, draft=False, preview=False):
    path = Path(root) / 'data/gomi-support.json'
    if preview and (not draft or Path(out).resolve() == Path(root).resolve()):
        raise ValueError('--gomi-preview requires --draft and a separate --out directory')
    if not path.exists():
        if preview:
            raise ValueError('Missing gomi-support.json')
        return None
    data = json.loads(path.read_text())
    if data.get('draft', True) and not preview:
        if (Path(out) / 'gomi-support.html').exists():
            raise ValueError('Unreviewed gomi pages already exist in --out; use a fresh output directory')
        return None
    from validate_gomi import validate
    errors = validate(data, root=Path(root), publication=not preview)
    if errors:
        raise ValueError('Gomi data validation failed: ' + '; '.join(errors))
    return data


def city_path(city):
    pref, slug = city['id'].split(':')
    return f'{pref}-gomi-support/{slug}.html'


def update_home(soup, data):
    """Run after the existing colorful-home pass; leave regional search intact."""
    for old in soup.select('.home-topic-jump, #gomi-support-entry'):
        old.decompose()
    title = '免許返納・移動・ごみ出しの支援を地域から探す｜じもとくらべ'
    description = '免許返納の特典や移動支援を全国の市町村から探せます。ごみ出し支援は掲載地域を確認し、日常ごみ・粗大ごみの条件、回収場所、相談先を調べられます。'
    soup.title.string = title
    for selector, value in [('meta[name="description"]', description), ('meta[property="og:title"]', title), ('meta[property="og:description"]', description)]:
        node = soup.select_one(selector)
        if node:
            node['content'] = value
    hero = soup.select_one('.warm-home-hero')
    hero.h1.clear()
    hero.h1.append(BeautifulSoup('免許返納・移動・ごみ出し。<br><span>地域の支援を、家族と。</span>', 'html.parser'))
    hero.select_one('.lead').string = '自分や家族が使える支援の条件と、相談先を確認できます。まずは、探したい内容から。'
    hero.select_one('.warm-speech').clear()
    hero.select_one('.warm-speech').append(BeautifulSoup('これからの暮らし、<br>一緒に考えてみよう。', 'html.parser'))
    portrait = hero.select_one('.warm-portrait img')
    if portrait:
        portrait['alt'] = '親子で地域の案内を読み、暮らしの支援を相談するイラスト'
    nav = BeautifulSoup('<nav class="home-topic-jump" aria-label="探したい支援"><a href="#prefectures">免許返納・移動の支援</a><a href="#gomi-support-entry">ごみ出しの支援</a></nav>', 'html.parser')
    hero.select_one('.intro').append(nav)
    directory = soup.select_one('#prefectures')
    heading = directory.select_one('h2')
    icon = heading.find('svg')
    if icon:
        icon.extract()
    heading.string = '免許返納・移動の支援を探す'
    if icon:
        heading.insert(0, icon)
    directory.select_one('.section-head p').string = '全国の都道府県 → 市町村の順に選べます。ごみ出しは下の専用入口から。'
    soup.select_one('#search-title').string = '移動の支援を市町村名から探す'
    support = soup.select_one('.home-support')
    support.h2.string = '移動のページで確認できること'
    support.select_one('p.muted').string = '免許返納の特典と、返納を条件にしない移動支援を分けて案内します。'
    names = '・'.join(escape(c['name']) for c in data['cities'])
    links = ''.join(f'<a href="{city_path(c)}">{escape(c["name"])}</a>' for c in data['cities'])
    directory.insert_after(BeautifulSoup(f'''<section class="home-gomi-entry" id="gomi-support-entry" aria-labelledby="home-gomi-title">
      <div><p class="eyebrow">日常の袋ごみも、家具などの粗大ごみも</p><h2 id="home-gomi-title">ごみを運び出せないとき</h2>
      <p>玄関まで出せるか、室内から難しいか。回収場所と対象条件を分けて、相談先を確認できます。</p>
      <p class="home-gomi-coverage">掲載地域：{names}。未掲載の地域は、支援がないという意味ではありません。</p>
      <a class="home-gomi-main" href="gomi-support.html">ごみ出し支援を探す <span aria-hidden="true">→</span></a>
      <nav class="home-gomi-cities" aria-label="ごみ出し支援の掲載地域">{links}</nav></div>
      <div class="home-gomi-distinction" aria-label="回収場所を分けて確認"><p>日常のごみ出し</p><strong>玄関先？ 集積所？</strong><hr><p>粗大ごみの搬出</p><strong>室内から頼める？</strong><span>支援ごとに条件が異なります</span></div>
    </section>''', 'html.parser'))
    # Keep the home WebSite description aligned if this later becomes publishable.
    for script in soup.select('script[data-seo-markup]'):
        graph = json.loads(script.string)
        for item in graph.get('@graph', []):
            if item.get('@type') == 'WebSite':
                item['description'] = description
        script.string = json.dumps(graph, ensure_ascii=False).replace('</', '<\\/')


def render(out, root, data, *, draft=True):
    from gomi_pages import generate_pages
    from seo_markup import inject
    out, root = Path(out), Path(root)
    pages = generate_pages(data, draft=draft)
    for relative, content in pages.items():
        path = out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(inject(content, relative), encoding='utf-8')
    for name in ('gomi-support.css', 'gomi-support.js'):
        if out.resolve() != root.resolve():
            shutil.copy2(root / 'assets' / name, out / 'assets' / name)
    # Complete a fresh preview without replacing assets the main build generated.
    if out.resolve() != root.resolve():
        for asset in (root / 'assets').rglob('*'):
            target = out / asset.relative_to(root)
            if asset.is_file() and not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(asset, target)
    home_path = out / 'index.html'
    soup = BeautifulSoup(home_path.read_text(), 'html.parser')
    update_home(soup, data)
    home_path.write_text(str(soup), encoding='utf-8')
    for city in data['cities']:
        pref, slug = city['id'].split(':')
        page = out / f'{pref}-menkyo-henno/{slug}.html'
        soup = BeautifulSoup(page.read_text(), 'html.parser')
        for old in soup.select('#gomi-related'):
            old.decompose()
        link = BeautifulSoup(f'<section class="block" id="gomi-related" data-related-support><h2>ごみを運び出せないとき</h2><p>日常のごみ出しと粗大ごみの搬出を分けて、対象条件・回収場所・相談先を確認できます。免許返納は利用条件ではありません。</p><a href="../{city_path(city)}">{escape(city["name"])}のごみ出し支援を見る →</a></section>', 'html.parser')
        (soup.select_one('.content') or soup.main).append(link)
        page.write_text(str(soup), encoding='utf-8')
    if draft:
        (out / 'robots.txt').write_text('User-agent: *\nDisallow: /\n')
        (out / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>\n')
    else:
        ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
        ET.register_namespace('', ns)
        tree = ET.parse(out / 'sitemap.xml')
        existing = {n.text for n in tree.findall('.//{'+ns+'}loc')}
        for relative in pages:
            url = 'https://jimotokurabe.jp/' + relative
            if url not in existing:
                ET.SubElement(ET.SubElement(tree.getroot(), '{'+ns+'}url'), '{'+ns+'}loc').text = url
        tree.write(out / 'sitemap.xml', encoding='utf-8', xml_declaration=True)
    return list(pages)
