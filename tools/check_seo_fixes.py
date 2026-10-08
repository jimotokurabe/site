"""Focused regressions for the October SEO/analytics audit."""
from pathlib import Path
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
urls = [x.text for x in ET.parse(ROOT/'sitemap.xml').findall('.//s:loc', ns)]
for url in urls:
    path = url.removeprefix('https://jimotokurabe.jp/') or 'index.html'
    html = (ROOT/path).read_text()
    assert html.count('name = "official_info_click"') == 1, path
    assert "if (/^(www\\.)?jimotokurabe\\.jp$/.test(location.hostname)) gtag('config'" in html, path
s = BeautifulSoup((ROOT/'kanagawa-menkyo-henno/yokohama.html').read_text(), 'html.parser')
for tag in s(['script', 'style']): tag.decompose()
text = s.get_text(' ', strip=True)
for stale in ('令和8年度以降', '今回は再調査せず', '最後まで未照合', '"return":'):
    assert stale not in text, stale
assert '令和9年度以降' in text and '2026-10-08' in text
assert '受付を終了しました' in text
s = BeautifulSoup((ROOT/'hyogo-menkyo-henno/nishinomiya.html').read_text(), 'html.parser')
for fragment in ('statewide', 'extra', 'steps-h'):
    links = s.select(f'a[href="#{fragment}"]')
    assert links and s.find(id=fragment), fragment
    assert not s.find(string=lambda x: x and x.strip() == '#'+fragment), fragment
print(f'PASS: {len(urls)} pages each have one tracker; Yokohama content and Nishinomiya links verified')
