"""Regressions for the five published-page review findings."""
import copy
import json
from pathlib import Path
import unittest
from bs4 import BeautifulSoup
from gomi_pages import _service_html, _value, _value_html
from validate_gomi import validate

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'data/gomi-support.json').read_text())
SERVICES = {s['id']: s for c in DATA['cities'] for s in c['services']}
SOURCES = {s['id']: s for s in DATA['sources']}

class GomiReviewTests(unittest.TestCase):
    def test_akashi_conditions_keep_common_and_alternative_branches(self):
        value = SERVICES['akashi-daily']['fields']['eligibility']['value']
        common, alternatives = value['all']
        self.assertEqual(len(common['all']), 2)
        self.assertIn('ステーション', common['all'][0])
        self.assertIn('高齢・障害・年少', common['all'][1])
        elderly, disability = alternatives['any']
        self.assertEqual(len(elderly['all']), 3)
        self.assertIn('65歳', elderly['all'][0])
        self.assertIn('要介護2', elderly['all'][1])
        self.assertIn('ホームヘルプ', elderly['all'][2])
        self.assertIn('第28条第1項', disability['all'][1])
        self.assertIn('「居宅介護」または「生活介護」', disability['all'][1])
        self.assertNotIn('65歳', _value(disability))
        self.assertNotIn('要介護2', _value(disability))
        self.assertIn('親族等や近隣住民', value['exclusion'])
        self.assertIn('審査', value['note'])
        html = BeautifulSoup(_value_html(value), 'html.parser')
        self.assertEqual(len(html.select('[data-condition="any"] > ul > li')), 2)
        self.assertEqual(len(html.select('[data-condition="any"] [data-condition="all"]')), 2)

    def test_nested_conditions_keep_labels_exceptions_and_escaped_text(self):
        value = {'all': ['共通条件', {'any': [{'label': '<条件>', 'all': ['A', 'B']}, 'C']}], 'exception': '相談', 'exclusion': '除外'}
        html = BeautifulSoup(_value_html(value), 'html.parser')
        self.assertIsNone(html.find('条件'))
        self.assertIn('<条件>', html.get_text())
        self.assertIn('A\n', _value(value))
        self.assertEqual(len(html.select('[data-condition="any"] [data-condition="all"] > ul > li')), 2)
        self.assertIn('除外', html.get_text())

    def test_unconfirmed_services_keep_contact_and_questions_outside_details(self):
        for sid in ['nishi-carry', 'akashi-carry']:
            service = SERVICES[sid]
            soup = BeautifulSoup(_service_html(service, SOURCES, DATA['checked'], False), 'html.parser')
            details = soup.select_one('.gomi-unconfirmed-details')
            self.assertNotIn('open', details.attrs)
            self.assertEqual(len(details.select('.gomi-fact')), 9)
            self.assertIsNone(soup.select_one('[data-field="contact"]').find_parent('details'))
            self.assertIsNone(soup.select_one('.gomi-service-questions').find_parent('details'))
            self.assertTrue(soup.select_one('[data-field="contact"] a[href^="tel:"]'))
            self.assertIn('断定するものではありません', soup.select_one('.gomi-not-found').get_text())
            self.assertIn(service['search_scope'], details.get_text())
            self.assertTrue(details.select('a[href^="https:"]'))

    def test_yokohama_contact_links_are_actions_not_only_citations(self):
        for sid in ['yokohama-daily', 'yokohama-carry']:
            soup = BeautifulSoup(_service_html(SERVICES[sid], SOURCES, DATA['checked'], False), 'html.parser')
            link = soup.select_one('[data-field="contact"] .gomi-contact-link')
            self.assertEqual(link['href'], SOURCES['yokohama-offices']['url'])
            self.assertIn('電話番号', link.get_text())
            self.assertIsNone(link.find_parent(class_='gomi-field-sources'))
        for sid, source in SOURCES.items():
            if sid.startswith('yokohama-'):
                self.assertNotEqual(source['title'], '横浜市トップページ')

    def test_contact_link_needs_registered_cited_source(self):
        data = copy.deepcopy(DATA)
        contact = data['cities'][0]['services'][0]['fields']['contact']
        contact['links'] = [{'source_id': 'missing', 'label': '窓口'}]
        self.assertTrue(any('.links:' in error for error in validate(data, ROOT)))

    def test_invalid_logic_and_question_shape_fail_validation(self):
        data = copy.deepcopy(DATA)
        service = data['cities'][0]['services'][0]
        service['fields']['eligibility']['value'] = {'any': 'wrong shape'}
        service['questions_for_office'] = 'wrong shape'
        errors = validate(data, ROOT)
        self.assertTrue(any('non-empty condition list' in error for error in errors))
        self.assertTrue(any('list of non-empty questions' in error for error in errors))

if __name__ == '__main__':
    unittest.main()
