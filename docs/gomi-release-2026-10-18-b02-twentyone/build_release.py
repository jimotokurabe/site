"""Render only the approved waste hierarchy and home waste entry."""
from pathlib import Path
import json,sys,subprocess
from bs4 import BeautifulSoup
R=Path(__file__).resolve().parents[2];H=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'tools'))
from gomi_pages import generate_pages
from seo_markup import inject
from gomi_integration import home_entry
D=json.loads((R/'data/gomi-support.json').read_text());B=json.loads((H/'base-data.json').read_text());P=json.loads((H/'plan.json').read_text())
pages=generate_pages(D,draft=False)
for c in B['cities']:
 path=c['id'].replace(':','-gomi-support/')+'.html'
 old=BeautifulSoup(subprocess.check_output(['git','show',P['pre_release_head']+':'+path],cwd=R,text=True),'html.parser');new=BeautifulSoup(pages[path],'html.parser')
 for selector in ('.gomi-kind','.gomi-memo','.gomi-local-notice','.gomi-research-note','.gomi-sources','.gomi-route-nav'):
  assert [str(x) for x in old.select(selector)]==[str(x) for x in new.select(selector)],(path,selector)
for path,html in pages.items():
 target=R/path;target.parent.mkdir(exist_ok=True);target.write_text(inject(html,path))
p=R/'index.html';raw=p.read_text();old=str(BeautifulSoup(raw,'html.parser').select_one('#gomi-support-entry'));assert raw.count(old)==1;p.write_text(raw.replace(old,home_entry(D)))
p=R/'sitemap.xml';raw=p.read_text();missing=['https://jimotokurabe.jp/'+path for path in pages if 'https://jimotokurabe.jp/'+path not in raw];baseline_sitemap=subprocess.check_output(['git','show',P['pre_release_head']+':sitemap.xml'],cwd=R,text=True);expected={url for url in ['https://jimotokurabe.jp/'+path for path in pages] if url not in baseline_sitemap};assert len(expected)==12 and set(missing)<=expected
p.write_text(raw.replace('</urlset>',''.join('<url><loc>'+url+'</loc></url>' for url in missing)+'</urlset>'))
print('Generated 32 waste pages (10 prefectures / 21 cities / national hub), home waste block; sitemap +12 URLs. Old 19 city records/memos unchanged.')
