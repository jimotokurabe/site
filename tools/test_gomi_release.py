"""Reject accidental publication or cross-city use of candidate sources."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from gomi_integration import prepare
from validate_gomi import validate
ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'data/gomi-support.json').read_text())

class CandidateBoundaries(unittest.TestCase):
    def test_kawasaki_source_is_city_scoped_and_faq_is_exact(self):
        for url, allowed in (
            ('https://www.city.kawasaki.jp/templates/faq/300/0000013341.html', True),
            ('https://www.sodai.city.kawasaki.jp/eco/view/kawasaki/faq.html', True),
            ('https://www.sodai.city.kawasaki.jp/other.html', False),
            ('https://evil.www.city.kawasaki.jp/', False),
        ):
            for owner in ('kanagawa:kawasaki', 'hyogo:kobe'):
                data = copy.deepcopy(DATA)
                data['cities'] = [data['cities'][0]]
                data['cities'][0]['id'] = owner
                src = data['sources'][0]
                src['id'] = 'kawasaki-dropoff-faq'; src['url'] = url
                data['sources'] = [src]
                for service in data['cities'][0]['services']:
                    for fact in service['fields'].values():
                        fact['source_ids'] = ['kawasaki-dropoff-faq']
                errors = validate(data, ROOT)
                rejected = any('sources[0].url:' in e for e in errors)
                self.assertEqual(rejected, not (allowed and owner == 'kanagawa:kawasaki'), (url, owner))

    def test_external_data_never_enters_normal_or_in_repo_build(self):
        for opts in ({}, {'draft': True}, {'preview': True}):
            with self.assertRaises(ValueError):
                prepare(ROOT, '/tmp/gomi-test', data_path='/missing.json', **opts)
        with self.assertRaises(ValueError):
            prepare(ROOT, ROOT / 'private-output', draft=True, preview=True, data_path='/missing.json')

    def test_draft_candidate_requires_approval_even_with_review(self):
        data = copy.deepcopy(DATA)
        data.pop('publication_approval', None)
        data['not_for_publication'] = True
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'candidate.json'
            p.write_text(json.dumps(data))
            self.assertEqual(prepare(ROOT, Path(td)/'out', draft=True, preview=True, data_path=p), data)
            self.assertTrue(validate(data, ROOT, publication=True))

    def test_amagasaki_sources_cannot_be_reused_for_other_cities(self):
        for url in ('https://www.city.amagasaki.hyogo.jp/kurashi/gomi/manner/bunbetu/036_oogata.html',
                    'https://faq.city.amagasaki.hyogo.jp/faq/detail.aspx?id=287',
                    'https://faq.city.amagasaki.hyogo.jp/faq/detail.aspx?id=999',
                    'https://evil.www.city.amagasaki.hyogo.jp/'):
            data = copy.deepcopy(DATA)
            src = data['sources'][0]
            old_id = src['id']; src['id'] = 'amagasaki-faq287'; src['url'] = url
            for c in data['cities']:
                for s in c['services']:
                    for f in s['fields'].values():
                        f['source_ids'] = ['amagasaki-faq287' if x == old_id else x for x in f['source_ids']]
            self.assertTrue(any('.url:' in e for e in validate(data, ROOT)))

if __name__ == '__main__':
    unittest.main()
