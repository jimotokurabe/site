"""Publish three owner-approved municipalities; preserve all existing pages."""
from pathlib import Path
import json,sys,subprocess
R=Path(__file__).resolve().parents[2];H=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'tools'))
from gomi_pages import generate_pages
from seo_markup import inject
D=json.loads((R/'data/gomi-support.json').read_text());P=json.loads((H/'plan.json').read_text());pages=generate_pages(D,draft=False)
for name,html in pages.items():
 target=R/name;content=inject(html,name)
 if target.exists() and name!='gomi-support.html' and name not in {pid+'-gomi-support/index.html' for pid in P['changed_prefecture_ids']}:assert target.read_text()==content,'Existing page changed: '+name
 else:target.parent.mkdir(exist_ok=True);target.write_text(content)
p=R/'sitemap.xml';raw=p.read_text();missing=['https://jimotokurabe.jp/'+path for path in pages if 'https://jimotokurabe.jp/'+path not in raw];baseline=subprocess.check_output(['git','show',P['pre_release_head']+':sitemap.xml'],cwd=R,text=True);expected={url for url in ['https://jimotokurabe.jp/'+path for path in pages] if url not in baseline};assert len(expected)==12 and set(missing)<=expected
p.write_text(raw.replace('</urlset>',''.join('<url><loc>'+url+'</loc></url>' for url in missing)+'</urlset>'))
print('Generated/compared 50 waste pages: existing 24 cities/10 unaffected prefectures unchanged; added 12 cities, updated 3 prefectures, national hub and sitemap +12. Home unchanged.')
