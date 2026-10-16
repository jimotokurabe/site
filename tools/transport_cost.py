"""Render the transport estimate template inside the public site frame."""

from pathlib import Path
import json

from bs4 import BeautifulSoup

from site_header import apply_site_header


TEMPLATE = Path(__file__).resolve().parent / 'templates' / 'transport-cost.html.tmpl'


def transport_cost_page(shell, draft=False):
    write_estimates()
    source = BeautifulSoup(TEMPLATE.read_text(encoding='utf-8'), 'html.parser')
    source_main = source.select_one('main')
    if source_main is None or (source_main.get('id') != 'tc-app' and source_main.select_one('#tc-app') is None):
        raise ValueError('Transport estimate template requires main and #tc-app')
    title = source.title.get_text(' ', strip=True) if source.title else '移動費の目安｜じもとくらべ'
    description_tag = source.select_one('meta[name="description"]')
    description = (description_tag.get('content', '') if description_tag else '') or '地域を選んで、タクシー・バスの支援を使う場合の移動費を概算できます。'
    raw = shell(title=title, description=description, path='transport-cost.html',
                main='<div id="tc-app">'+source_main.decode_contents()+'</div>', draft=draft)
    soup = BeautifulSoup(raw, 'html.parser')
    soup.body['class'] = ['transport-cost-page']
    soup.main['class'] = ['transport-cost-main']
    mast = soup.select_one('.topbar')
    mast['class'] = ['mast']
    mast.select_one('.sizer')['class'] = ['size']
    # The shared menu's display setting is handled by site-header.js.
    for script in soup.select('script:not([src])'):
        if 'jk-size' in script.get_text():
            script.decompose()
    for link in soup.select('link[href]'):
        if 'fonts.google' in link['href']:
            link.decompose()
    boot = soup.new_tag('script')
    boot.string = "try{document.documentElement.classList.toggle('large',sessionStorage.getItem('jk-national-size')==='large')}catch(e){}"
    soup.head.append(boot)
    for link in source.head.select('link[href]'):
        if link['href'].split('?', 1)[0] == 'assets/transport-cost.css':
            soup.head.append(link)
    apply_site_header(soup)
    for script in source.select('script[src]'):
        if script['src'].split('?', 1)[0] in ('assets/transport-cost-engine.js', 'assets/transport-cost.js'):
            if script['src'].split('?', 1)[0] == 'assets/transport-cost.js':
                script['src'] = 'assets/transport-cost.js?v=analytics-20261016'
            soup.body.append(script)
    return str(soup)


def write_estimates():
    root = TEMPLATE.parents[2]
    verified = json.loads((root / 'data/transport-estimate-verified.json').read_text())
    reviewed_path = root / 'data/transport-estimate-reviewed.json'
    reviewed = json.loads(reviewed_path.read_text()) if reviewed_path.exists() else []
    if not isinstance(reviewed, list):
        reviewed = reviewed['rules']
    known = {r['key'] for r in verified}
    rules = verified + [r for r in reviewed if r['key'] not in known]
    ids = set()
    catalogs = {}
    for rule in rules:
        if rule['id'] in ids:
            raise ValueError('Duplicate estimate rule: ' + rule['id'])
        ids.add(rule['id'])
        if rule.get('origin') == 'record':
            pid, cid = rule['key'].split(':', 1)
            if pid not in catalogs:
                catalogs[pid] = json.loads((root / 'assets/outing-supports' / (pid + '.json')).read_text())
            city = next(c for c in catalogs[pid]['cities'] if c['id'] == cid)
            original = next(p for p in city['programs'] if p['id'] == rule['programId'])
            evidence = next((d['text'].strip() for d in original['details'] if d['label'] == '支援内容'), '')
            if not original['selectable'] or original['checked'] != rule['checked'] or evidence != rule['evidence'] or original['sources'] != rule['sources']:
                raise ValueError('Recorded estimate must be reviewed again: ' + rule['key'])
        if not rule.get('sources') or not rule.get('checked'):
            raise ValueError('Estimate needs source and original confirmation date')
    target = root / 'assets/transport-estimates.json'
    target.write_text(json.dumps(rules, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return rules
