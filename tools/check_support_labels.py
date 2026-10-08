"""Regression checks for misleading positive support labels and rendered parity."""
from pathlib import Path
import json
from bs4 import BeautifulSoup
from support_labels import support_labels
ROOT = Path(__file__).resolve().parents[1]

def texts(c, b=None, t=None):
    return [x['text'] for x in support_labels(c, b, t)]

for state in ['end', 'none', 'notfound', 'unrecognized']:
    assert not texts({'k': state})
assert texts({'k': 'give'}) == ['返納特典あり']
assert texts({'k': 'give', 'flag': '原文未確認'}) == ['返納特典 要確認']
assert texts({'k': 'give', 'dl': '2020年3月31日まで'}) == ['返納特典 要確認']
assert texts({'k': 'give', 'dl': '返納から6か月以内'}) == ['返納特典あり']
assert not texts({}, {'status': 'ended', 'programs': [{'kind': 'pass', 'current': 'document_checked'}]})
assert texts({}, {'status': 'active', 'programs': [{'kind': 'pass', 'current': 'needs_confirmation'}]}) == ['バス助成 要確認']
assert texts({}, {'status': 'henno', 'programs': [{'kind': 'henno', 'current': 'document_checked'}]}) == ['バス助成あり（返納が条件）']
assert not texts({}, None, {'k': 'yes', 'name': '乗合交通', 'what': '1回700円で運行', 'note': '別に助成制度もあります'})
assert texts({}, None, {'k': 'care', 'what': 'タクシー券を交付'}) == ['タクシー助成あり（要介護等の条件）']
for state in ['end', 'notfound', 'none']:
    assert not texts({}, None, {'k': state, 'what': '以前はタクシー券を交付'})

def record(pid, slug, suffix):
    d = json.loads((ROOT/'data'/f'{pid}-{suffix}.json').read_text())['cities']
    return d.get(slug) if isinstance(d, dict) else next(c for c in d if c['slug'] == slug)

def real(pid, slug):
    return texts(*(record(pid, slug, suffix) for suffix in ['menkyo-henno', 'bus', 'taxi']))
assert real('hyogo', 'nishinomiya') == ['バス助成あり', 'タクシー助成あり（要介護等の条件）']
assert real('hyogo', 'kobe') == ['バス助成あり']
assert real('hyogo', 'akashi') == ['返納特典あり', 'バス助成あり', 'タクシー助成あり']
assert '返納特典あり' in real('kanagawa', 'yokohama')
# Check static prefecture lists against the exact data sent to home search.
soup = BeautifulSoup((ROOT/'index.html').read_text(), 'html.parser')
script = next(t.string for t in soup.find_all('script') if t.string and 'const cities=' in t.string)
cities, _ = json.JSONDecoder().raw_decode(script.split('const cities=', 1)[1])
assert len(cities) == 1741
prefs = {}
for c in cities:
    if c['pid'] not in prefs:
        prefs[c['pid']] = BeautifulSoup((ROOT/(c['pid']+'-menkyo-henno.html')).read_text(), 'html.parser')
    a = prefs[c['pid']].select_one(f'.citylist a[href="{c["url"]}"]')
    assert a is not None, c['url']
    assert [x.get_text() for x in a.select('.support-label')] == [x['text'] for x in c['labels']], c['url']
print('PASS: support classification, real city examples, and 1741 search/list label matches')
