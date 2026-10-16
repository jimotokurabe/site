"""Regression checks for draft boundaries and preserved deep links."""
from pathlib import Path
import tempfile
import unittest
from build import shell
from national_pages import capture_legacy_ids


class AnalyticsGenerationTests(unittest.TestCase):
    def test_draft_has_no_analytics_bootstrap(self):
        for draft in (True, False):
            html = shell(title='Title', description='Description', path='test.html', main='', draft=draft)
            self.assertEqual(html.count('data-jk-analytics="gtag"'), 0 if draft else 1)
            self.assertNotIn('googletagmanager.com/gtag/js', html)

    def test_capture_city_anchors_before_intermediate_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test-menkyo-henno').mkdir()
            (root / 'test-menkyo-henno/city.html').write_text('<h2 id="quick-answer-title">Title</h2><span id="verify"></span>')
            # Home's waste module is regenerated later; copying this anchor first duplicates it.
            (root / 'index.html').write_text('<h2 id="home-gomi-title">Waste</h2>')
            before = capture_legacy_ids(root)
            (root / 'test-menkyo-henno/city.html').write_text('<main></main>')
            self.assertEqual(before, {'test-menkyo-henno/city.html': {'quick-answer-title', 'verify'}})


if __name__ == '__main__':
    unittest.main()
