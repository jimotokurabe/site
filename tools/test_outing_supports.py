"""Safety and fidelity checks for the outing support catalog."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup
from outing_supports import catalog, city_links, program, write_catalog


class OutingSupportTests(unittest.TestCase):
    def bus(self, **changes):
        data = {'name': '敬老パス', 'current': 'document_checked', 'age_min': 70,
                'eligibility': '70歳以上。福祉パス対象者を除く。',
                'benefit': '小児料金を負担。無料ではありません。',
                'notes': ['対象外の区間あり。', '利用前に窓口で確認。'],
                'sources': [{'url': 'https://www.city.kobe.lg.jp/pass.html',
                             'label': '市の公式案内', 'checked': '2026-10-05',
                             'updated': '2026-08-01'}]}
        data.update(changes)
        return data

    def test_unusable_states_never_become_selectable(self):
        for state in ('ended', 'end', 'notfound', 'unknown', 'none', 'needs_confirmation'):
            with self.subTest(state=state):
                self.assertFalse(program('hyogo', 'kobe', 'bus', self.bus(current=state), '2026-10-06')['selectable'])
                self.assertFalse(program('hyogo', 'kobe', 'bus', self.bus(), '2026-10-06', {'status': state})['selectable'])
        for state in ('end', 'notfound', 'unknown', 'none'):
            record = {'k': state, 'current': 'active', 'url': 'https://www.city.kobe.lg.jp/taxi.html'}
            self.assertFalse(program('hyogo', 'kobe', 'taxi', record, '2026-10-06')['selectable'])

    def test_sources_required_and_unsafe_sources_rejected(self):
        for url in ('javascript:alert(1)', 'data:text/html,x', '//city.example.jp/pass',
                    'https://user:password@city.example.jp/', 'http://127.0.0.1/',
                    'http://localhost/', 'https://city.example.jp/\npass', 'https://city.example.jp\\@evil.test/'):
            with self.subTest(url=url):
                p = program('hyogo', 'kobe', 'bus', self.bus(sources=[{'url': url}]), '2026-10-06')
                self.assertFalse(p['selectable'])
                self.assertEqual(p['sources'], [])
        self.assertFalse(program('hyogo', 'kobe', 'bus', self.bus(sources=[]), '2026-10-06')['selectable'])
        self.assertFalse(program('hyogo', 'kobe', 'bus', self.bus(current='new_state'), '2026-10-06')['selectable'])

    def test_dates_sources_and_complete_conditions_retained(self):
        record = self.bus(checked='2026-10-04', routes='対象路線。' * 300)
        p = program('hyogo', 'kobe', 'bus', record, '2026-10-06')
        self.assertTrue(p['selectable'])
        self.assertEqual(p['checked'], '2026-10-04')
        self.assertEqual(p['sources'], record['sources'])
        texts = [d['text'] for d in p['details']]
        self.assertIn(record['eligibility'], texts)
        self.assertIn({'label': '記録上の対象年齢の下限', 'text': '70'}, p['details'])
        self.assertIn(record['routes'], texts)
        self.assertIn('\n'.join(record['notes']), texts)
        self.assertEqual(p['page'], 'hyogo-menkyo-henno/kobe.html#support')

    def test_care_and_multi_program_taxi_stay_one_conditional_record(self):
        record = {'k': 'care', 'name': '福祉タクシー・移送支援',
                  'age': '要介護4・5。市民税非課税世帯。',
                  'amt': 'Aは月2枚、Bは年48枚。併用不可。',
                  'url': 'https://www.city.kobe.lg.jp/taxi.html', 'src': '市の案内',
                  'more_sources': [{'url': 'https://www.city.kobe.lg.jp/taxi.pdf', 'label': '利用条件'}]}
        p = program('hyogo', 'kobe', 'taxi', record, '2026-09-26')
        self.assertTrue(p['selectable'])
        self.assertEqual(p['name'], record['name'])
        self.assertEqual(len(p['sources']), 2)
        self.assertIn({'label': '対象・年齢', 'text': record['age']}, p['details'])
        self.assertIn({'label': '支援内容', 'text': record['amt']}, p['details'])

    def test_id_stable_across_order_dates_and_conditions(self):
        a = self.bus()
        a['sources'].append({'url': 'https://www.city.kobe.lg.jp/pass.pdf', 'label': '詳細'})
        b = dict(a, sources=list(reversed(a['sources'])), eligibility='条件の記録を更新', checked='2026-10-09')
        self.assertEqual(program('hyogo', 'kobe', 'bus', a, '2026-10-06')['id'],
                         program('hyogo', 'kobe', 'bus', b, '2026-10-09')['id'])
        self.assertNotEqual(program('hyogo', 'kobe', 'bus', a, '')['id'],
                            program('hyogo', 'kobe', 'bus', dict(a, name='別制度'), '')['id'])

    def test_empty_city_retained_and_writer_reusable(self):
        d = {'pref': {'id': 'hyogo', 'name': '兵庫県'}, 'checked': '2026-10-06',
             'cities': [{'slug': 'kobe', 'n': '神戸市'}]}
        gathered = ({'hyogo': d}, {}, {}, {'records': {}}, {})
        with patch('outing_supports.gather', return_value=gathered), tempfile.TemporaryDirectory() as directory:
            index, prefs = write_catalog('.', directory)
            self.assertEqual(index['prefectures'][0]['cities'], [{'id': 'kobe', 'name': '神戸市'}])
            city = prefs['hyogo']['cities'][0]
            self.assertEqual(city['programs'], [])
            self.assertEqual(city['page'], 'hyogo-menkyo-henno/kobe.html')
            self.assertEqual(json.loads((Path(directory) / 'assets/outing-supports/hyogo.json').read_text()), prefs['hyogo'])

    def test_exact_heading_and_section_fallback_links(self):
        p = program('hyogo', 'kobe', 'bus', self.bus(), '2026-10-06')
        city = {'programs': [p]}
        soup = BeautifulSoup('<section id="support"><article><h3>敬老パス</h3></article></section><section id="taxi"></section>', 'html.parser')
        city_links(soup, 'hyogo', 'kobe', city)
        link = soup.select_one('#support [data-outing-support-link]')
        self.assertEqual(parse_qs(urlsplit(link['href']).query)['support'], [p['id']])
        self.assertEqual(urlsplit(link['href']).path, '../outing-plan.html')
        city_links(soup, 'hyogo', 'kobe', city)
        self.assertEqual(len(soup.select('#support [data-outing-support-link]')), 1)
        for content in ('<h3>表示名が異なる</h3>', '<h3>敬老パス</h3><h3>敬老パス</h3>'):
            soup = BeautifulSoup('<section id="support">' + content + '</section>', 'html.parser')
            city_links(soup, 'hyogo', 'kobe', city)
            query = parse_qs(urlsplit(soup.a['href']).query)
            self.assertEqual(query, {'pref': ['hyogo'], 'city': ['kobe'], 'type': ['bus']})

    def test_accepted_supplements_stay_at_city_scope(self):
        d = {'pref': {'id': 'hyogo', 'name': '兵庫県'}, 'checked': '2026-10-06',
             'cities': [{'slug': 'kobe', 'n': '神戸市'}]}
        accepted = {'reviewed': True, 'safety_accepted': True, 'value': '本人乗車。入院中は対象外。',
                    'source': 'https://www.city.kobe.lg.jp/conditions.pdf', 'evidence': '照合用原文'}
        pending = dict(accepted, reviewed=False, value='未採用の内容')
        supplements = {'records': {'hyogo:kobe': {'checked': '2026-10-03', 'updates': [accepted, pending],
                                                  'unresolved': ['併用条件は要確認。']}}}
        bus = {'hyogo': {'checked': '2026-10-06', 'cities': [{'slug': 'kobe', 'status': 'active',
                                                           'programs': [self.bus()]}]}}
        with patch('outing_supports.gather', return_value=({'hyogo': d}, bus, {}, supplements, {})):
            _, prefs = catalog('.')
        city = prefs['hyogo']['cities'][0]
        self.assertEqual(city['supplements'][0], {'label': '確認済みの補足', 'text': accepted['value'],
                                                 'source': accepted['source'], 'checked': '2026-10-03'})
        self.assertEqual(city['supplements'][1]['text'], '併用条件は要確認。')
        encoded = json.dumps(city, ensure_ascii=False)
        self.assertNotIn('照合用原文', encoded)
        self.assertNotIn('未採用の内容', encoded)
        self.assertNotIn(accepted['value'], json.dumps(city['programs'], ensure_ascii=False))

    def test_single_aggregated_taxi_links_its_record(self):
        p = program('hyogo', 'kobe', 'taxi', {'k': 'care', 'name': '福祉タクシー・移送支援',
                    'url': 'https://www.city.kobe.lg.jp/taxi.html'}, '2026-10-06')
        soup = BeautifulSoup('<section id="taxi"><h3>タクシーの支援</h3></section>', 'html.parser')
        city_links(soup, 'hyogo', 'kobe', {'programs': [p]})
        self.assertEqual(parse_qs(urlsplit(soup.a['href']).query),
                         {'pref': ['hyogo'], 'city': ['kobe'], 'support': [p['id']]})

    def test_real_catalog_paths_and_rejected_records(self):
        root = Path(__file__).resolve().parents[1]
        index, prefs = catalog(root)
        self.assertEqual(len(index['prefectures']), 47)
        self.assertEqual([p['id'] for p in index['prefectures'][:3]], ['hokkaido', 'aomori', 'iwate'])
        self.assertEqual(index['prefectures'][-1]['id'], 'okinawa')
        for pref in prefs.values():
            for city in pref['cities']:
                self.assertTrue((root / city['page']).is_file(), city['page'])
                ids = [p['id'] for p in city['programs']]
                self.assertEqual(len(ids), len(set(ids)), city['key'])
                for p in city['programs']:
                    if p['selectable']:
                        self.assertTrue(p['sources'])
                        self.assertTrue(p['checked'])
        kobe = next(c for c in prefs['hyogo']['cities'] if c['id'] == 'kobe')
        self.assertTrue(any(p['type'] == 'bus' and p['selectable'] for p in kobe['programs']))
        self.assertTrue(all(not p['selectable'] for p in kobe['programs'] if p['type'] == 'taxi'))
        takarazuka = next(c for c in prefs['hyogo']['cities'] if c['id'] == 'takarazuka')
        self.assertTrue(all(not p['selectable'] for p in takarazuka['programs'] if p['type'] == 'taxi'))


if __name__ == '__main__':
    unittest.main()
