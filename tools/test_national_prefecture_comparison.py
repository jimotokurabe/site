"""Coverage, provenance and navigation contracts across the 47 data sets."""
import json
from pathlib import Path
import unittest
from bs4 import BeautifulSoup
from prefecture_comparison import comparison_rows, row_html
from build import taxi_block, taxi_card, guide_taxi_mobility

ROOT = Path(__file__).resolve().parents[1]


class NationalComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.datasets = {}
        for path in sorted((ROOT/'data').glob('*-menkyo-henno.json')):
            pref = json.loads(path.read_text()); pid = pref['pref']['id']
            bus = json.loads((ROOT/'data'/f'{pid}-bus.json').read_text())
            taxi = json.loads((ROOT/'data'/f'{pid}-taxi.json').read_text())
            cls.datasets[pid] = pref, bus, taxi, comparison_rows(pref, bus, taxi)

    def test_complete_coverage_in_all_three_categories(self):
        self.assertEqual(len(self.datasets), 47)
        self.assertEqual(sum(len(data[0]['cities']) for data in self.datasets.values()), 1741)
        for pid, (pref, bus, _, rows) in self.datasets.items():
            cities = {city['slug'] for city in pref['cities']}
            for kind in ('return', 'bus', 'taxi'):
                self.assertEqual({row['slug'] for row in rows if row['kind'] == kind}, cities, (pid, kind))
            self.assertEqual(sum(row['kind'] == 'bus' for row in rows), sum(max(1, len(city['programs'])) for city in bus['cities']))

    def test_detail_destinations_stay_in_their_prefecture(self):
        for pid, (_, _, _, rows) in self.datasets.items():
            for row in rows:
                soup = BeautifulSoup(row_html(row), 'html.parser')
                self.assertEqual(soup.select_one('.comparison-detail')['href'], f'{pid}-menkyo-henno/{row["slug"]}.html#{row["anchor"]}')

    def test_all_bus_conditions_fares_and_cautions_are_preserved(self):
        for pid, (_, bus, _, rows) in self.datasets.items():
            for city in bus['cities']:
                for program in city['programs']:
                    row = next(row for row in rows if row['kind'] == 'bus' and row['slug'] == city['slug'] and row['name'] == program['name'])
                    money = [text for _, text in row['money']]
                    self.assertIn(program['benefit'], money, (pid, city['slug']))
                    self.assertIn(program['fare'], money, (pid, city['slug']))
                    self.assertIn(('対象・条件', program['eligibility']), row['conditions'])
                    for note in program.get('notes', []):
                        self.assertIn(note, row['notes'])

    def test_tax_conditions_amounts_and_confirmation_dates_are_original(self):
        for pid, (pref, bus, taxi, rows) in self.datasets.items():
            for city in pref['cities']:
                t = taxi['cities'][city['slug']]
                row = next(row for row in rows if row['kind'] == 'taxi' and row['slug'] == city['slug'])
                for key in ('age', 'henno_link', 'how'):
                    if t.get(key) and t[key] != '記載なし':
                        self.assertIn(t[key], [text for _, text in row['conditions']])
                if t.get('amt') and t['k'] not in ('end', 'none', 'notfound', 'unknown') and t['amt'] != '記載なし':
                    self.assertIn(t['amt'], [text for _, text in row['money']])
                self.assertEqual(row['checked'], t.get('checked') or taxi['checked'])
                ret = next(row for row in rows if row['kind'] == 'return' and row['slug'] == city['slug'])
                self.assertEqual(ret['checked'], city.get('checked') or pref['checked'])

    def test_unconfirmed_bus_amounts_show_caution_next_to_the_amount(self):
        tested = 0
        for _, (_, _, _, rows) in self.datasets.items():
            for row in rows:
                if row['state'] == 'needs_confirmation':
                    soup = BeautifulSoup(row_html(row), 'html.parser')
                    self.assertIn('現在の条件・金額は確認が必要', soup.select_one('td[data-label="支援内容・金額"]').get_text())
                    tested += 1
        expected = sum(program.get('current') == 'needs_confirmation'
                       for _, bus, _, _ in self.datasets.values() for city in bus['cities'] for program in city['programs'])
        self.assertGreater(tested, 0)
        self.assertEqual(tested, expected)

    def test_return_only_taxi_conditions_survive_all_legacy_renderers(self):
        pref = self.datasets['aichi'][0]['pref']
        city = {'slug': 'example', 'n': '確認市', 'y': 'かくにんし'}
        record = {'k': 'henno_only', 'what': '返納者に交付する選択制のタクシー券。',
                  'age': '市内在住65歳以上で全免許を自主返納した人。',
                  'amt': '2,000円分、1人1回。バス券との選択。',
                  'how': '返納から1年以内に取消通知書を持参。',
                  'checked': '2026-10-31'}
        for html in (taxi_block(record, '市'), taxi_card(city, record, pref),
                     guide_taxi_mobility(city, record, pref, '../')):
            text = BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)
            for field in ('age', 'amt', 'how'):
                self.assertIn(record[field], text)
            self.assertIn('返納者のみ', text)
        duplicate = dict(record, age='記載なし', amt='記載なし', how='記載なし')
        for html in (taxi_block(duplicate, '市'), taxi_card(city, duplicate, pref),
                     guide_taxi_mobility(city, duplicate, pref, '../')):
            self.assertNotIn('ページに記載なし', BeautifulSoup(html, 'html.parser').get_text())


if __name__ == '__main__':
    unittest.main()
