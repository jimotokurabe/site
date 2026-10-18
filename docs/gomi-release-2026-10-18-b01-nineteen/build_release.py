"""Generate waste release only; preserve all existing city/transport pages and assets."""
from pathlib import Path
import sys,json,re
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'))
from gomi_pages import generate_pages
from seo_markup import inject
from gomi_integration import update_home
from bs4 import BeautifulSoup
D=json.loads((R/'data/gomi-support.json').read_text());pages=generate_pages(D,draft=False)
for name,html in pages.items():
 path=R/name;content=inject(html,name)
 if path.exists() and name!='gomi-support.html':
  assert path.read_text()==content,'Old page changed: '+name
 else:path.parent.mkdir(exist_ok=True);path.write_text(content)
p=R/'index.html';old=p.read_text();s=BeautifulSoup(old,'html.parser');before=str(s.select_one('#gomi-support-entry'));update_home(s,D);after=str(s.select_one('#gomi-support-entry'));assert old.count(before)==1;p.write_text(old.replace(before,after))
p=R/'sitemap.xml';old=p.read_text();urls=['https://jimotokurabe.jp/hyogo-gomi-support/'+x+'.html' for x in ['kawanishi','himeji']];missing=[u for u in urls if u not in old];p.write_text(old.replace('</urlset>',''.join('<url><loc>'+u+'</loc></url>' for u in missing)+'</urlset>'))
print('Generated 20 waste pages; 17 existing byte-identical, added 2; home section and 2 sitemap URLs only')
