"""Publication boundaries and coverage, independent of the UI rendering."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from gomi_integration import prepare, update_home, city_path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'data/gomi-support.json').read_text())


class GomiIntegrationTests(unittest.TestCase):
    def test_preview_requires_draft_and_separate_output(self):
        with self.assertRaises(ValueError):
            prepare(ROOT, '/tmp/gomi-test', preview=True, draft=False)
        with self.assertRaises(ValueError):
            prepare(ROOT, ROOT, preview=True, draft=True)

    def test_normal_build_omits_unreviewed_data(self):
        research = copy.deepcopy(DATA)
        research['draft'] = True
        with tempfile.TemporaryDirectory() as out, patch('gomi_integration.json.loads', return_value=research):
            self.assertIsNone(prepare(ROOT, out))
            (Path(out) / 'gomi-support.html').write_text('stale preview')
            with self.assertRaises(ValueError):
                prepare(ROOT, out)

    def test_preview_accepts_research_but_public_gate_rejects_flag_only_change(self):
        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(prepare(ROOT, out, draft=True, preview=True)['cities'], DATA['cities'])
            temp_root = Path(out) / 'repo'
            (temp_root / 'data').mkdir(parents=True)
            changed = copy.deepcopy(DATA)
            changed['draft'] = False
            (temp_root / 'data/gomi-support.json').write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                prepare(temp_root, Path(out) / 'build')

    def test_home_retains_all_existing_municipality_and_prefecture_links(self):
        soup = BeautifulSoup((ROOT / 'index.html').read_text(), 'html.parser')
        original = [a['href'] for a in soup.select('#prefectures a[href]')]
        original_scripts = [s.get_text() for s in soup.find_all('script') if 'const cities=' in s.get_text()]
        update_home(soup, DATA)
        self.assertEqual(original, [a['href'] for a in soup.select('#prefectures a[href]')])
        self.assertEqual(original_scripts, [s.get_text() for s in soup.find_all('script') if 'const cities=' in s.get_text()])
        self.assertIn('免許返納・移動', soup.select_one('#prefectures h2').get_text())
        hrefs = {a['href'] for a in soup.select('#gomi-support-entry a')}
        self.assertEqual(hrefs, {'gomi-support.html'})
        self.assertIn('都道府県から探す', soup.select_one('#gomi-support-entry').get_text())
        self.assertEqual(len(soup.select('h1')), 1)


if __name__ == '__main__':
    unittest.main()
