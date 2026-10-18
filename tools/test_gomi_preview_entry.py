import unittest
from build_gomi_preview import replace_home_entry

class PreviewEntryTest(unittest.TestCase):
    def test_preserves_bytes_around_nested_entry(self):
        before = '<html>  <!-- preserve -->'
        after = '\n<footer data-z="x" class="y">KEEP</footer>'
        old = '<section class="x" id="gomi-support-entry"><section>nested</section></section>'
        self.assertEqual(replace_home_entry(before + old + after, '<section>NEW</section>'), before + '<section>NEW</section>' + after)
    def test_rejects_missing_duplicate_and_unclosed(self):
        for raw in ('<section></section>', '<section id="gomi-support-entry"></section>' * 2, '<section id="gomi-support-entry">'):
            with self.assertRaises(ValueError): replace_home_entry(raw, 'NEW')
