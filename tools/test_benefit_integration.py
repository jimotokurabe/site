"""Behavior and retention checks for the four-panel presentation transform."""
import unittest
from bs4 import BeautifulSoup

from benefit_integration import ITEMS, apply_benefit_integration


def page():
    return BeautifulSoup('''<html><head></head><body class="compact-city"><main>
      <section class="intro"><h2>この地域で使える支援を確認</h2>
      <div class="compact-highlights"><a class="compact-highlight" href="#support">
      <svg></svg><strong>バス</strong><span class="condition">70歳以上・除外条件あり</span>
      <span class="value">小児運賃</span></a></div>
      <ul class="overview">''' + ''.join('<li><a href="#' + key + '"><svg></svg><strong>' + key +
      '</strong></a></li>' for key in ('benefit', 'taxi', 'rides')) + '''</ul>
      <p class="compact-note">掲載がない項目は、制度がないことを示すものではありません。</p></section>
      <div class="layout"><nav class="side"><a href="#statewide">県共通特典</a></nav><div class="content">
      <section id="benefit" class="block compact-status"><h2>返納支援</h2>
      <p>受付は終了。1人1回、1種類です。</p><article id="statewide"><h3 id="sw-h">県共通</h3>
      <details><summary>条件</summary><p>65歳以上・現金のみ。</p>
      <a href="https://example.jp/pref">公式出典</a></details></article><p>確認日：2026-09-26</p></section>
      <section id="support" class="block"><h2 id="bus-title">敬老パス</h2>
      <p>福祉パスの対象者を除きます。</p><a href="https://example.jp/bus">バス公式</a>
      <a class="outing-support-link" href="../outing.html?support=bus">計画で使う</a></section>
      <section id="taxi" class="block compact-status"><h2>タクシー</h2><p>地区条件あり。</p></section>
      <section id="rides" class="block compact-status"><h2>交通</h2><p>個別路線は未掲載です。</p></section>
      <section id="procedure"><h2>返納手続き</h2><a href="../test.html#return-procedure">県の手続き</a></section>
      <section id="family"><h2>家族と確認</h2><label><input type="checkbox">条件を確認</label>
      <button data-share-city>共有メモ</button></section></div></div></main>
      <script src="../assets/national-city.js"></script></body></html>''', 'html.parser')


class BenefitIntegrationTests(unittest.TestCase):
    def test_records_are_moved_once_with_text_links_and_dates_intact(self):
        soup = page()
        before = {key: (soup.select_one('#' + key).get_text(' ', strip=True),
                       [a['href'] for a in soup.select('#' + key + ' a[href]')]) for key in ITEMS}
        procedure = str(soup.select_one('#procedure'))
        apply_benefit_integration(soup)
        for key, (text, links) in before.items():
            with self.subTest(key=key):
                original = soup.select_one('#record-' + key)
                self.assertEqual(original.get_text(' ', strip=True), text)
                self.assertEqual([a['href'] for a in original.select('a[href]')], links)
                self.assertEqual(len(soup.select('#' + key)), 1)
                self.assertIs(original.parent, soup.select_one('#' + key))
        self.assertEqual(str(soup.select_one('#procedure')), procedure)
        self.assertEqual(len(soup.select('#family input[type="checkbox"]')), 1)
        self.assertIsNotNone(soup.select_one('#family [data-share-city]'))
        self.assertEqual(soup.select_one('#support')['aria-labelledby'], 'bus-title')
        self.assertEqual(len(soup.select('#statewide')), 1)
        self.assertEqual(len(soup.select('#sw-h')), 1)

    def test_existing_known_first_entrances_and_unknown_distinction_survive(self):
        soup = page()
        compact_text = soup.select_one('.intro').get_text(' ', strip=True)
        apply_benefit_integration(soup)
        self.assertEqual(soup.select_one('.intro').get_text(' ', strip=True), compact_text)
        self.assertEqual([p['id'] for p in soup.select('.integrated-panel')],
                         ['support', 'benefit', 'taxi', 'rides'])
        self.assertEqual([a['data-pick'] for a in soup.select('.is-unknown')],
                         ['benefit', 'taxi', 'rides'])
        self.assertEqual(len(soup.select('.intro svg')), 4)
        self.assertIsNotNone(soup.select_one('.compact-highlight'))
        self.assertIsNotNone(soup.select_one('.overview'))

    def test_no_js_fallback_does_not_hide_panels_or_wrap_conditions_in_disclosure(self):
        soup = page()
        apply_benefit_integration(soup)
        self.assertNotIn('integrated-enhanced', soup.body.get('class', []))
        for panel in soup.select('.integrated-panel'):
            self.assertFalse(panel.has_attr('hidden'))
            self.assertIsNone(panel.find_parent('details'))
            self.assertIsNone(panel.select_one('.original-record').find_parent('details'))
        self.assertEqual(len(soup.select('details')), 2)  # Existing source detail and local procedure.
        self.assertIsNotNone(soup.select_one('details.retained-procedure > #procedure'))
        self.assertEqual(soup.select_one('.procedure-jump a')['href'], '../test.html#return-procedure')
        self.assertEqual(soup.select_one('#family').find('h2').find_next_sibling()['id'], 'selected-benefits')

    def test_transform_is_idempotent_and_adds_no_external_action(self):
        soup = page()
        links = [a['href'] for a in soup.select('a[href^="https:"]')]
        apply_benefit_integration(soup)
        once = str(soup)
        apply_benefit_integration(soup)
        self.assertEqual(str(soup), once)
        self.assertCountEqual([a['href'] for a in soup.select('a[href^="https:"]')], links)
        self.assertEqual(len(soup.select('#selection-dialog')), 1)
        self.assertEqual(len(soup.select('[data-add-family]')), 4)

    def test_missing_record_or_entrance_fails_explicitly(self):
        for selector in ('#taxi', '.overview li:last-child'):
            with self.subTest(selector=selector):
                soup = page()
                soup.select_one(selector).decompose()
                with self.assertRaises(ValueError):
                    apply_benefit_integration(soup)

    def test_empty_legacy_alias_outside_record_is_nested_with_benefit(self):
        soup = page()
        soup.select_one('#sw-h').decompose()
        soup.main.append(soup.new_tag('span', id='sw-h', attrs={'class': 'legacy-anchor'}))
        apply_benefit_integration(soup)
        self.assertEqual(len(soup.select('#sw-h')), 1)
        self.assertEqual(soup.select_one('#sw-h').find_parent(class_='integrated-panel')['id'], 'benefit')

    def test_historical_nested_record_is_moved_once_into_its_own_panel(self):
        soup = page()
        soup.select_one('#support').append(soup.select_one('#benefit').extract())
        original = {key: str(soup.select_one('#' + key)) for key in ITEMS}
        apply_benefit_integration(soup)
        self.assertEqual(len(soup.select('.benefit-panels > .integrated-panel')), 4)
        self.assertIsNone(soup.select_one('#support #benefit'))
        self.assertEqual(soup.get_text().count('受付は終了。1人1回、1種類です。'), 1)
        self.assertEqual(soup.select_one('#record-benefit').get_text(' ', strip=True),
                         BeautifulSoup(original['benefit'], 'html.parser').get_text(' ', strip=True))

    def test_extra_intro_cross_reference_is_not_a_fifth_entrance(self):
        soup = page()
        extra = soup.new_tag('a', href='#support')
        extra.string = 'バス欄でも確認'
        soup.select_one('.intro').append(extra)
        apply_benefit_integration(soup)
        self.assertEqual(len(soup.select('[data-pick]')), 4)
        self.assertFalse(extra.has_attr('data-pick'))


if __name__ == '__main__':
    unittest.main()
