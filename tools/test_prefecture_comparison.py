import json
from pathlib import Path
import unittest
from bs4 import BeautifulSoup
from prefecture_comparison import comparison_rows, row_html, enhance_prefecture

ROOT = Path(__file__).resolve().parents[1]


class ComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pref, cls.bus, cls.taxi = [json.loads((ROOT/'data'/f'hyogo-{name}.json').read_text()) for name in ('menkyo-henno', 'bus', 'taxi')]
        cls.rows = comparison_rows(cls.pref, cls.bus, cls.taxi)

    def test_every_city_and_bus_program_present(self):
        for kind in ('return', 'bus', 'taxi'):
            rows = [row for row in self.rows if row['kind'] == kind]
            self.assertEqual({row['slug'] for row in rows}, {city['slug'] for city in self.pref['cities']})
        self.assertEqual(sum(row['kind'] == 'bus' for row in self.rows), sum(max(1, len(city['programs'])) for city in self.bus['cities']))

    def test_bus_amounts_eligibility_exclusions_and_sources_are_verbatim(self):
        for city in self.bus['cities']:
            for program in city['programs']:
                row = next(row for row in self.rows if row['kind'] == 'bus' and row['slug'] == city['slug'] and row['name'] == program['name'])
                text = BeautifulSoup(row_html(row), 'html.parser').get_text(' ', strip=True)
                for field in ('eligibility', 'benefit', 'fare'):
                    self.assertIn(program[field], text)
                for note in program.get('notes', []):
                    self.assertIn(note, text)
                for source in program['sources']:
                    self.assertIn(source['url'], row_html(row).replace('&amp;', '&'))

    def test_ended_and_unconfirmed_amounts_are_not_current_awards(self):
        for kind, slug, state in [('return', 'kobe', 'end'), ('return', 'nishinomiya', 'none'), ('return', 'himeji', 'notfound'), ('taxi', 'kobe', 'notfound')]:
            row = next(row for row in self.rows if row['kind'] == kind and row['slug'] == slug)
            self.assertEqual(row['state'], state)
            self.assertNotEqual(row['money'][0][1], '0円')
        kobe = next(row for row in self.rows if row['kind'] == 'return' and row['slug'] == 'kobe')
        self.assertEqual(kobe['money'][0][1], '受付終了')

    def test_frequency_deposit_budget_and_deadline_are_kept(self):
        expectations = {'taishi': ['1回だけ', '2027年3月31日'], 'akashi': ['預り金500円', '2026年4月', '2027年3月31日'],
                        'kawanishi': ['予算', '1人1回', '2025年4月1日'], 'taka': ['1人1年に1冊', '1,000円']}
        for slug, terms in expectations.items():
            row = next(row for row in self.rows if row['kind'] == 'return' and row['slug'] == slug)
            text = BeautifulSoup(row_html(row), 'html.parser').get_text(' ', strip=True)
            for term in terms:
                self.assertIn(term, text)

    def test_confirmation_dates_follow_the_individually_reviewed_record(self):
        returns = {city['slug']: city for city in self.pref['cities']}
        buses = {city['slug']: city for city in self.bus['cities']}
        for row in self.rows:
            if row['kind'] == 'return':
                expected = returns[row['slug']].get('checked') or self.pref['checked']
            elif row['kind'] == 'taxi':
                expected = self.taxi['cities'][row['slug']].get('checked') or self.taxi['checked']
            else:
                city = buses[row['slug']]
                program = next((p for p in city['programs'] if p['name'] == row['name']), {})
                expected = program.get('checked') or city.get('checked') or self.bus['checked']
            self.assertEqual(row['checked'], expected)
            self.assertIn(row['checked'], row_html(row))

    def test_validity_is_not_mislabeled_as_application_deadline(self):
        row = next(row for row in self.rows if row['kind'] == 'return' and row['slug'] == 'kasai')
        self.assertIn(('有効期限', '利用者証を発行した年から、5年後の誕生日まで'), row['money'])
        self.assertFalse(any(label == '申請期限' and '5年後' in text for label, text in row['conditions']))

    def test_deposits_frequency_and_personal_cost_are_visible_beside_money(self):
        for slug, terms in {'akashi': ['預り金500円'], 'kawanishi': ['預り金500円'],
                            'taka': ['1人1年に1冊', '1,000円'], 'taishi': ['1回だけ']}.items():
            row = next(row for row in self.rows if row['kind'] == 'return' and row['slug'] == slug)
            text = ' '.join(value for _, value in row['money'])
            for term in terms:
                self.assertIn(term, text)

    def test_input_values_are_escaped(self):
        row = dict(self.rows[0], money=[('内容', '<script>alert(1)</script>')])
        self.assertNotIn('<script>', row_html(row))
        self.assertIn('&lt;script&gt;', row_html(row))

    def test_custom_city_taxi_panels_include_the_reviewed_evidence(self):
        for pref, slug in [('hyogo', 'kobe'), ('kanagawa', 'yokohama')]:
            with self.subTest(city=slug):
                record = json.loads((ROOT/'data'/f'{pref}-taxi.json').read_text())['cities'][slug]
                panel = BeautifulSoup((ROOT/f'{pref}-menkyo-henno'/f'{slug}.html').read_text(), 'html.parser').select_one('#taxi')
                text = panel.get_text(' ', strip=True)
                for field in ('what', 'note', 'checked'):
                    self.assertIn(record[field], text)
                links = {link.get('href') for link in panel.select('a[href]')}
                self.assertIn(record['url'], links)
                for source in record.get('more_sources', []):
                    self.assertIn(source['url'], links)


if __name__ == '__main__':
    unittest.main()
