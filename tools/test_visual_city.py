"""Small regressions for rearranging existing records without altering facts."""
from collections import Counter
import unittest

from bs4 import BeautifulSoup
from visual_city import apply_visual_city


def page(body):
    return BeautifulSoup('<html><head></head><body><main>' + body + '</main></body></html>', 'html.parser')


def section(rows):
    return '<section id="benefit"><h2 id="title">返納支援</h2><dl class="facts">' + rows + '</dl></section>'


def row(label, value, attrs=''):
    return '<div ' + attrs + '><dt>' + label + '</dt><dd>' + value + '</dd></div>'


def original_strings(soup):
    # Remove only newly inserted visual copy and decorative SVG, keeping source text.
    copy = BeautifulSoup(str(soup), 'html.parser')
    for item in copy.select('svg, .visual-program-caption, .visual-detail > summary'):
        item.decompose()
    return Counter(s.strip() for s in copy.stripped_strings)


class VisualCityTests(unittest.TestCase):
    def test_full_original_prose_is_retained(self):
        soup = page(section(row('支援内容', '券は10枚。併用不可。') + row('対象', '70歳以上の市民のみ。') + row('申請期限', '返納から6か月以内。')))
        before = original_strings(soup)
        apply_visual_city(soup, {'return': {'k': 'yes'}})
        self.assertEqual(original_strings(soup), before)
        self.assertIsNone(soup.find(string='返納から6か月以内。').find_parent('details'))

    def test_links_and_existing_ids_survive_moving_rows(self):
        soup = page(section(row('対象', '<span id="age">70歳以上</span>', 'id="eligibility"') + row('支援内容', '<a id="source" href="https://example.org/benefit">案内</a>')))
        ids = Counter(t['id'] for t in soup.select('[id]'))
        hrefs = Counter(t['href'] for t in soup.select('a[href]'))
        apply_visual_city(soup, {'return': {}})
        self.assertEqual(Counter(t['id'] for t in soup.select('[id]')), ids)
        self.assertEqual(Counter(t['href'] for t in soup.select('a[href]')), hrefs)

    def test_nested_definition_list_is_preserved(self):
        nested = '<dl class="facts" id="nested"><div><dt>対象</dt><dd>障害等級の条件あり</dd></div></dl>'
        soup = page(section(row('対象', nested) + row('支援内容', '利用券')))
        before = str(soup.find(id='nested'))
        apply_visual_city(soup, {'return': {}})
        self.assertEqual(str(soup.find(id='nested')), before)
        self.assertIsNone(soup.find(id='nested').find_parent(class_='visual-facts'))

    def test_source_disclosure_keeps_links_and_each_date(self):
        value = '<ul><li><a href="https://example.org/a">出典A</a> 確認日：2026-10-01</li><li><a href="https://example.org/b">出典B</a> 確認日：2026-10-04</li></ul>'
        soup = page(section(row('公式出典', value)))
        before = original_strings(soup)
        apply_visual_city(soup, {'return': {}})
        self.assertEqual(original_strings(soup), before)
        self.assertEqual(len(soup.select('.visual-detail a')), 2)

    def test_long_application_with_conditions_stays_visible(self):
        soup = page(section(row('申請方法', '窓口で申請できます。' * 30 + '本人確認書類が必要です。')))
        apply_visual_city(soup, {'return': {}})
        self.assertIsNone(soup.select_one('.visual-fact-apply details'))

    def test_long_unconditional_application_can_fold_without_loss(self):
        prose = '地域の担当窓口へご相談ください。' * 30
        soup = page(section(row('申請方法', '<span id="contact">' + prose + '</span>')))
        apply_visual_city(soup, {'return': {}})
        self.assertIsNotNone(soup.select_one('.visual-fact-apply details'))
        self.assertEqual(soup.find(id='contact').get_text(), prose)

    def test_ended_unknown_and_notfound_have_state_classes(self):
        for state, expected in [('end', 'ended'), ('unknown', 'unknown'), ('notfound', 'unknown')]:
            with self.subTest(state=state):
                soup = page(section(row('支援内容', '元の掲載記録')))
                apply_visual_city(soup, {'return': {'k': state}})
                self.assertIn('visual-state-' + expected, soup.find(id='benefit')['class'])
                self.assertIn('元の掲載記録', soup.get_text())

    def test_archives_remain_untouched_and_transform_is_idempotent(self):
        soup = page(section(row('支援内容', '現行の掲載記録')) + '<section id="support"><details class="archive"><summary>過去の記録</summary><dl class="facts" id="historic"><div><dt>支援内容</dt><dd>終了した券</dd></div></dl></details></section>')
        archive = str(soup.find(id='historic'))
        apply_visual_city(soup, {'return': {}, 'bus': {'status': 'ended'}})
        first = str(soup)
        apply_visual_city(soup, {'return': {}, 'bus': {'status': 'ended'}})
        self.assertEqual(str(soup), first)
        self.assertEqual(str(soup.find(id='historic')), archive)


if __name__ == '__main__':
    unittest.main()
