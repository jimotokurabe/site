"""Focused editorial-retention tests; no build or production data writes."""
import copy
import unittest

from bs4 import BeautifulSoup

from compact_city import apply_compact_city
from compact_records import (
    BUS_PRESENT, RETURN_PRESENT, TAXI_PRESENT, display_record, unsupported_negative,
)
from national_city import guide_body


def sample_page():
    choices = ''.join(
        f'<li><a href="#{anchor}"><svg class="visual-picture" aria-label="{anchor}"></svg>'
        f'<strong>{anchor}</strong><span class="condition">対象条件</span>'
        '<span class="value">掲載内容</span></a></li>'
        for anchor in ('benefit', 'support', 'taxi', 'rides')
    )
    return BeautifulSoup(
        '<html><head></head><body><main><section class="intro">'
        '<div class="section-head"><h2>目的</h2><p>案内</p></div>'
        f'<ul class="overview">{choices}</ul></section>'
        '<section id="benefit"><p class="important">受付は2023年12月28日で終了しました。</p>'
        '<div class="unknown"><p>代理申請では本人確認書類も必要です。</p></div></section>'
        '<section id="support"></section><section id="taxi"></section>'
        '<section id="rides"></section></main></body></html>', 'html.parser',
    )


def adopted(state='end', shared=False):
    return {'return': {'k': state}, 'bus': {'status': 'unknown'},
            'taxi': {'k': state}, 'statewide': {'body': ['県共通割引']} if shared else {},
            'common': {}, 'mobility': []}


class CompactRetentionTests(unittest.TestCase):
    def test_single_unsourced_placeholder_changes_only_display(self):
        record = {'k': 'notfound', 'what': '村独自の特典は見つかりませんでした。',
                  'checked': '2026-10-01', 'notes': ['問い合わせは福祉課です。']}
        original = copy.deepcopy(record)
        result = display_record(record)
        self.assertNotIn('what', result)
        self.assertIn('記録が不足', result['record_status'])
        self.assertEqual(result['notes'], record['notes'])
        self.assertEqual(result['checked'], record['checked'])
        self.assertEqual(record, original)

    def test_multisentence_negative_remains_verbatim(self):
        value = '一般向けの割引はあります。返納者向けの追加特典は確認できませんでした。'
        record = {'k': 'notfound', 'what': value}
        self.assertFalse(unsupported_negative(record, 'what', value))
        self.assertEqual(display_record(record)["what"], record["what"])

    def test_conditional_negative_remains_verbatim(self):
        for value in (
            'ただし、要介護認定がある場合の利用条件は確認できませんでした。',
            '75歳以上の場合に限った追加助成は確認できませんでした。',
            '返納後1年以内の申請が条件となる特典は見つかりませんでした。',
        ):
            with self.subTest(value=value):
                record = {'k': 'notfound', 'what': value}
                self.assertFalse(unsupported_negative(record, 'what', value))
                self.assertEqual(display_record(record)["what"], record["what"])

    def test_sourced_negative_remains_verbatim(self):
        for source in ({'url': 'https://example.jp/city'},
                       {'sources': [{'url': 'https://example.jp/city', 'checked': '2026-09-01'}]}):
            with self.subTest(source=source):
                record = {'k': 'notfound', 'what': '独自の助成は見つかりませんでした。', **source}
                self.assertEqual(display_record(record)["what"], record["what"])

    def test_negative_and_uncertain_states_are_not_present(self):
        for present in (RETURN_PRESENT, TAXI_PRESENT, BUS_PRESENT):
            self.assertTrue(present.isdisjoint({'none', 'end', 'ended', 'unknown', 'notfound', None}))

    def test_municipal_guide_keeps_local_records_and_links_shared_procedure(self):
        guide = {'checked': '2026-09-15', 'cautions': ['代理申請には委任状が必要です。'],
                 'stations': [{'name': '市内窓口', 'tel': '0123-45-6789'}],
                 'sources': [{'url': 'https://example.jp/local', 'checked': '2026-09-14'}],
                 'extras': ['市内在住者のみ対象です。']}
        common = {'hennou': {'need': '県共通の持ち物一覧', 'url': 'https://example.jp/pref'}}
        soup = BeautifulSoup(guide_body(guide, common, '2026-01-01', '2026-02-02', 'test'), 'html.parser')
        text = soup.get_text(' ', strip=True)
        for value in ('代理申請には委任状が必要です。', '市内窓口', '0123-45-6789',
                      '市内在住者のみ対象です。', '2026-09-15', '2026-09-14'):
            self.assertIn(value, text)
        hrefs = {a['href'] for a in soup.select('a[href]')}
        self.assertIn('https://example.jp/local', hrefs)
        self.assertIn('../test-menkyo-henno.html#return-procedure', hrefs)
        self.assertNotIn('https://example.jp/pref', hrefs)
        self.assertNotIn('県共通の持ち物一覧', text)

    def test_four_illustrated_entrances_and_ended_caution_survive(self):
        soup = sample_page()
        apply_compact_city(soup, 'test', 'sample', adopted(shared=True))
        self.assertEqual(len(soup.select('.intro svg')), 4)
        self.assertEqual({a['href'] for a in soup.select('.intro a')},
                         {'#benefit', '#support', '#taxi', '#rides'})
        self.assertIn('受付は2023年12月28日で終了しました。', soup.select_one('#benefit').get_text())
        self.assertIn('代理申請では本人確認書類も必要です。', soup.select_one('#benefit').get_text())
        self.assertEqual(soup.select_one('.compact-highlight strong').get_text(), '県共通の返納支援')

    def test_absent_or_uncertain_benefits_are_not_highlighted(self):
        for state in ('none', 'end', 'unknown', 'notfound'):
            with self.subTest(state=state):
                soup = sample_page()
                apply_compact_city(soup, 'test', 'sample', adopted(state))
                self.assertFalse(soup.select('.compact-highlight'))
                self.assertEqual(len(soup.select('.intro svg')), 4)
                self.assertIn('掲載状況', soup.select_one('.intro h2').get_text())


if __name__ == '__main__':
    unittest.main()
