"""The waste guide keeps national, prefecture and city navigation separate."""
import copy
import json
from pathlib import Path
import unittest
from bs4 import BeautifulSoup
from gomi_pages import generate_pages, _prefecture_catalog
from gomi_integration import home_entry

ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/'data/gomi-support.json').read_text())

class GomiRegionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages=generate_pages(DATA,draft=True)

    def test_current_and_prior_nineteen_data_generate_only_covered_prefectures(self):
        for data in (DATA, {**DATA, 'cities':DATA['cities'][:19]}):
            pages=generate_pages(data,draft=True)
            prefs={c['id'].split(':')[0] for c in data['cities']}
            actual={p.split('-gomi-support/')[0] for p in pages if p.endswith('/index.html')}
            self.assertEqual(actual,prefs)
            self.assertEqual(len(pages),1+len(data['cities'])+len(prefs))

    def test_national_picker_has_47_prefectures_and_no_empty_prefecture_pages(self):
        soup=BeautifulSoup(self.pages['gomi-support.html'],'html.parser')
        tiles=soup.select('[data-gomi-pref]')
        self.assertEqual(len(tiles),47)
        self.assertEqual(len({a['data-gomi-pref'] for a in tiles}),47)
        for a in tiles:
            if a['href'].startswith('#'):
                self.assertEqual(a['href'],'#gomi-unlisted')
                self.assertNotIn(a['data-gomi-pref']+'-gomi-support/index.html',self.pages)
            else:self.assertIn(a['href'],self.pages)
        self.assertIn('支援制度がないという意味ではありません',soup.select_one('#gomi-unlisted').get_text())

    def test_city_finder_stays_secondary_and_uses_master_prefecture_names(self):
        soup=BeautifulSoup(self.pages['gomi-support.html'],'html.parser')
        finder=soup.select_one('[data-gomi-hub]')
        self.assertIsNotNone(finder.find_parent('details'))
        self.assertFalse(finder.find_parent('details').has_attr('open'))
        for row in finder.select('[data-city-search]'):
            self.assertNotIn('hyogo',row['data-city-search'])
        names={name for _,prefs in _prefecture_catalog() for _,name in prefs}
        self.assertTrue({x.get_text() for x in finder.select('.gomi-pref-name')}<=names)

    def test_county_pages_contain_only_their_own_cities_and_city_breadcrumbs_return(self):
        for city in DATA['cities']:
            pref,slug=city['id'].split(':')
            county=BeautifulSoup(self.pages[f'{pref}-gomi-support/index.html'],'html.parser')
            expected={c['id'].split(':')[1]+'.html' for c in DATA['cities'] if c['id'].split(':')[0]==pref}
            self.assertEqual({a['href'] for a in county.select('.gomi-city-card')},expected)
            soup=BeautifulSoup(self.pages[f'{pref}-gomi-support/{slug}.html'],'html.parser')
            crumbs=soup.select_one('.gomi-breadcrumb')
            self.assertEqual([a['href'] for a in crumbs.select('a')],['../index.html','../gomi-support.html','index.html'])
            self.assertEqual(crumbs.select_one('[aria-current="page"]').get_text(),city['name'])
            self.assertEqual(soup.select_one('.gomi-pref-back')['href'],'index.html')

    def test_pref_name_does_not_fall_back_to_internal_id(self):
        data=copy.deepcopy(DATA)
        for city in data['cities']:city.pop('pref_name',None)
        soup=BeautifulSoup(generate_pages(data,draft=True)['hyogo-gomi-support/index.html'],'html.parser')
        self.assertIn('兵庫県',soup.h1.get_text())
        self.assertEqual({x.get_text() for x in soup.select('.gomi-pref-name')},{'兵庫県'})

    def test_home_entrance_uses_one_national_cta(self):
        block=BeautifulSoup(home_entry(DATA),'html.parser')
        self.assertEqual([a['href'] for a in block.select('a')],['gomi-support.html'])
        self.assertIn('都道府県から探す',block.get_text())
        self.assertIn('都道府県 → 市町村',block.get_text())
        self.assertIsNone(block.select_one('.home-gomi-cities'))

if __name__=='__main__':unittest.main()
