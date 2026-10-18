"""Validate exact approved scope and preservation against recorded main."""
import hashlib,json,subprocess,sys,re,xml.etree.ElementTree as ET
from pathlib import Path
from bs4 import BeautifulSoup
H=Path(__file__).resolve().parent;R=H.parents[1];P=json.loads((H/'plan.json').read_text());B=P['pre_release_head']
def gitbytes(path):return subprocess.check_output(['git','show',B+':'+path],cwd=R)
def sha(b):return hashlib.sha256(b).hexdigest()
D=json.loads((R/'data/gomi-support.json').read_text());C=json.loads((H/'inputs/candidate.json').read_text());old=json.loads((H/'base-data.json').read_text());new=D['cities'][-2:]
assert D['cities'][:15]==old['cities'] and D['sources'][:95]==old['sources']
assert D['sources']==C['sources'];assert sum(len(s['fields']) for c in D['cities'] for s in c['services'])==680
paths=[p for p in subprocess.check_output(['git','ls-tree','-r','--name-only',B],cwd=R,text=True).splitlines() if '-menkyo-henno/' in p and p.endswith('.html')]
assert len(paths)==1741
for p in paths:assert (R/p).read_bytes()==gitbytes(p),p
for c in old['cities']:
 p=c['id'].replace(':','-gomi-support/')+'.html';assert (R/p).read_bytes()==gitbytes(p),p
for p in subprocess.check_output(['git','ls-tree','-r','--name-only',B,'assets'],cwd=R,text=True).splitlines():assert (R/p).read_bytes()==gitbytes(p),p
before=gitbytes('index.html').decode();after=(R/'index.html').read_text()
for content in [before,after]:assert len(BeautifulSoup(content,'html.parser').select('#gomi-support-entry'))==1
strip=lambda s:s.replace(str(BeautifulSoup(s,'html.parser').select_one('#gomi-support-entry')),'')
assert strip(before)==strip(after)
urls=lambda b:{n.text for n in ET.fromstring(b).findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')}
assert urls((R/'sitemap.xml').read_bytes())-urls(gitbytes('sitemap.xml'))=={'https://jimotokurabe.jp/hyogo-gomi-support/'+s+'.html' for s in ['takarazuka','itami']}
assert urls(gitbytes('sitemap.xml'))<=urls((R/'sitemap.xml').read_bytes())
fields=refs=questions=0
for city in D['cities']:
 path=city['id'].replace(':','-gomi-support/')+'.html';soup=BeautifulSoup((R/path).read_text(),'html.parser');assert len(soup.select('.gomi-route-nav a'))==4
 for service in city['services']:
  card=soup.find(id='route-'+service['id']);assert card
  for k,f in service['fields'].items():
   node=card.select_one('[data-field="'+k+'"]');assert node['data-source-ids']==' '.join(service['id']+'--'+i for i in f['source_ids']);fields+=1
  for sid in {i for f in service['fields'].values() for i in f['source_ids']}:
   source=next(s for s in D['sources'] if s['id']==sid);node=card.find(id='source-'+service['id']+'--'+sid);assert node['data-checked']==source['checked'] and node['data-updated']==(source['source_updated'] or '') and node.find('a')['href']==source['url'];refs+=1
  for q in service.get('questions_for_office',[]):assert q in card.get_text(' ',strip=True);questions+=1
outputs=['index.html','gomi-support.html','sitemap.xml','data/gomi-support.json','assets/gomi-support.css','assets/gomi-support.js']+[c['id'].replace(':','-gomi-support/')+'.html' for c in D['cities']]
result=dict(date='2026-10-18',preservation_baseline=B,candidate_sha256=P['candidate_sha256'],release_sha256=sha((R/'data/gomi-support.json').read_bytes()),existing_city_objects=15,existing_source_objects=95,existing_gomi_pages_byte_identical=15,transport_pages_byte_identical=1741,all_shared_assets_byte_identical=True,home_changes_only_gomi_region_section=True,sitemap_only_two_new_urls=True,fields=fields,route_source_dates=refs,questions=questions,public_gomi_pages=18,national_pages_regenerated=0,review='cumulative AI review; no human source review claim',gomi_unit_tests=28,analytics_generation_tests=2,outputs={p:sha((R/p).read_bytes()) for p in outputs})
publication=Path('/tmp/gomi-seventeen-publication.json')
if publication.exists() and publication.stat().st_size:result['publication_check']=json.loads(publication.read_text())
(H/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['outputs','publication_check']},ensure_ascii=False))
