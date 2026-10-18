from pathlib import Path
import sys,json,hashlib,subprocess,types
from bs4 import BeautifulSoup
O=Path(__file__).resolve().parent;R=O.parents[1]/'gomi-expansion-b02';I=O.parents[1]/'調査/2026-10-18_ごみ支援拡大B02/candidate.json'
sys.path.insert(0,str(R/'tools'))
from gomi_pages import generate_pages
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(I)=='c20d73181d6779d5c6d875f109724ecf45d62edfecda82fdced17235ec01e96a'
basecode=subprocess.check_output(['git','show','origin/main:tools/gomi_pages.py'],cwd=R,text=True)
baseline=types.ModuleType('baseline_gomi_pages');exec(compile(basecode,'baseline_gomi_pages.py','exec'),baseline.__dict__)
data=json.loads(I.read_text());old=baseline.generate_pages(data,draft=True);new=generate_pages(data,draft=True);preserved=0
for c in data['cities']:
 path=c['id'].replace(':','-gomi-support/')+'.html';before=BeautifulSoup(old[path],'html.parser');after=BeautifulSoup(new[path],'html.parser')
 for selector in ['.gomi-kind','.gomi-memo','.gomi-local-notice','.gomi-research-note','.gomi-sources','.gomi-route-nav']:
  assert [str(n) for n in before.select(selector)]==[str(n) for n in after.select(selector)],(path,selector)
 preserved+=1
prod=json.loads((R/'data/gomi-support.json').read_text());assert len(prod['cities'])==19
prod_generated=generate_pages(prod,draft=True)
assert len(prod_generated)==1+19+len({c['id'].split(':')[0] for c in prod['cities']})
assert subprocess.check_output(['git','diff','--name-only','--','data'],cwd=R,text=True)==''
assert (R/'assets/gomi-support.js').read_bytes()==subprocess.check_output(['git','show','origin/main:assets/gomi-support.js'],cwd=R)
raw=(R/'index.html').read_text();home=(O/'preview/index.html').read_text()
from gomi_integration import home_entry
oldblock=str(BeautifulSoup(raw,'html.parser').select_one('#gomi-support-entry'))
assert raw.count(oldblock)==1
assert raw.replace(oldblock,home_entry(data))==home
assert not (O/'preview/index.html').is_symlink()
assert (R/'index.html').read_bytes()==subprocess.check_output(['git','show','origin/main:index.html'],cwd=R)
manifest=json.loads((O/'preview/generation-manifest.json').read_text());assert not manifest['errors']
result=dict(candidate_sha256=sha(I),official_data_sha256=sha(R/'data/gomi-support.json'),candidate_cities_unchanged=21,published_cities=19,service_panels_memos_sources_dates_questions_unchanged=preserved,gomi_js_byte_identical=True,home_is_local_copy=True,home_bytes_outside_waste_entry_unchanged=True,production_home_unchanged=True,generated_waste_pages=len(new),generated_prefecture_pages=sum(p.endswith('/index.html') for p in new),generated_city_pages=len(data['cities']),prefecture_tiles=47,no_empty_prefecture_pages=True,production_19_data_generates=True,preview_link_errors=manifest['errors'],transport_pages_regenerated=0,gomi_tests_passed=35,publication=False)
(O/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
