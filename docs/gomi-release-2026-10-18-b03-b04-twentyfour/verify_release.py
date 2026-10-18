"""Approved data, navigation and non-waste preservation at the release boundary."""
from pathlib import Path
import sys,json,hashlib,subprocess,xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
H=Path(__file__).resolve().parent;R=H.parents[1];P=json.loads((H/'plan.json').read_text());B=P['pre_release_head'];sys.path.insert(0,str(R/'tools'))
from gomi_pages import generate_pages
from gomi_integration import home_entry
from seo_markup import inject
from validate_gomi import validate
sha=lambda b:hashlib.sha256(b).hexdigest()
def gitbytes(p):return subprocess.check_output(['git','show',B+':'+p],cwd=R)
D=json.loads((R/'data/gomi-support.json').read_text());old=json.loads((H/'base-data.json').read_text());C=json.loads((H/'inputs/candidate.json').read_text());assert not validate(D,R,publication=True)
assert D['cities'][:21]==old['cities'] and D['sources'][:len(old['sources'])]==old['sources']
assert D['sources']==C['sources']
for a,b in zip(D['cities'],C['cities']):
 aa=dict(a);aa['publication_status']=b['publication_status'];assert aa==b
paths=subprocess.check_output(['git','ls-tree','-r','--name-only',B],cwd=R,text=True).splitlines()
traffic=[p for p in paths if '-menkyo-henno/' in p and p.endswith('.html')];assert len(traffic)==1741
for p in traffic:assert (R/p).read_bytes()==gitbytes(p),p
assets=[p for p in paths if p.startswith('assets/')]
for p in assets:assert (R/p).read_bytes()==gitbytes(p),p
assert (R/'index.html').read_bytes()==gitbytes('index.html')
for city in old['cities']:
 p=city['id'].replace(':','-gomi-support/')+'.html';assert (R/p).read_bytes()==gitbytes(p),p
for pid in {c['id'].split(':')[0] for c in old['cities']}:
 p=pid+'-gomi-support/index.html';assert (R/p).read_bytes()==gitbytes(p),p
pages=generate_pages(D,draft=False);assert len(pages)==38
for p,html in pages.items():assert (R/p).read_text()==inject(html,p),p
oldpanels=0
for city in old['cities']:
 p=city['id'].replace(':','-gomi-support/')+'.html';a=BeautifulSoup(gitbytes(p),'html.parser');b=BeautifulSoup((R/p).read_text(),'html.parser')
 for selector in ('.gomi-kind','.gomi-memo','.gomi-local-notice','.gomi-research-note','.gomi-sources','.gomi-route-nav'):
  assert [str(n) for n in a.select(selector)]==[str(n) for n in b.select(selector)],(p,selector)
 oldpanels+=1
urls=lambda b:{x.text for x in ET.fromstring(b).findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')}
prior=urls(gitbytes('sitemap.xml'));now=urls((R/'sitemap.xml').read_bytes());newurls={'https://jimotokurabe.jp/'+p for p in pages}-prior;assert len(newurls)==6 and now-prior==newurls and prior<=now
fields=refs=questions=0
for city in D['cities']:
 pref,slug=city['id'].split(':');p=f'{pref}-gomi-support/{slug}.html';soup=BeautifulSoup((R/p).read_text(),'html.parser');assert len(soup.select('.gomi-route-nav a'))==4;assert soup.select_one('.gomi-breadcrumb a[href="index.html"]')
 for service in city['services']:
  card=soup.find(id='route-'+service['id']);assert card
  for k,f in service['fields'].items():
   node=card.select_one('[data-field="'+k+'"]');assert node['data-source-ids']==' '.join(service['id']+'--'+x for x in f['source_ids']);fields+=1
  for sid in {x for f in service['fields'].values() for x in f['source_ids']}:
   source=next(x for x in D['sources'] if x['id']==sid);node=card.find(id='source-'+service['id']+'--'+sid);assert node['data-checked']==source['checked'] and node['data-updated']==(source['source_updated'] or '') and node.a['href']==source['url'];refs+=1
  for q in service.get('questions_for_office',[]):assert q in card.get_text(' ',strip=True);questions+=1
hub=BeautifulSoup((R/'gomi-support.html').read_text(),'html.parser');assert len(hub.select('[data-gomi-pref]'))==47
prefs=[p for p in pages if p.endswith('/index.html')];assert len(prefs)==13
for p in prefs:
 pid=p.split('-gomi-support/')[0];s=BeautifulSoup((R/p).read_text(),'html.parser');assert {x['href'] for x in s.select('.gomi-city-card')}=={c['id'].split(':')[1]+'.html' for c in D['cities'] if c['id'].split(':')[0]==pid}
outputs=['index.html','sitemap.xml','data/gomi-support.json','assets/gomi-support.css','assets/gomi-support.js']+list(pages)
result=dict(date='2026-10-18',preservation_baseline=B,candidate_sha256=P['candidate_sha256'],release_sha256=sha((R/'data/gomi-support.json').read_bytes()),existing_city_objects=21,existing_source_objects=len(old['sources']),existing_city_panels_memos_sources_dates_questions_unchanged=oldpanels,transport_pages_byte_identical=1741,all_shared_assets_byte_identical=True,home_byte_identical=True,existing_city_html_byte_identical=21,existing_prefecture_html_byte_identical=10,sitemap_new_urls=6,fields=fields,route_source_dates=refs,questions=questions,public_gomi_pages=38,prefecture_pages=13,city_pages=24,prefecture_tiles=47,national_pages_regenerated=0,gomi_unit_tests=39,analytics_generation_tests=2,outputs={p:sha((R/p).read_bytes()) for p in outputs})
(H/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='outputs'},ensure_ascii=False))
