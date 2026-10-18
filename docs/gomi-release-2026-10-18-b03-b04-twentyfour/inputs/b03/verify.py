from pathlib import Path
import json,sys,hashlib,copy,subprocess
from bs4 import BeautifulSoup
O=Path(__file__).resolve().parent;R=O.parents[1];repo=R/'gomi-expansion-b03';sys.path.insert(0,str(repo/'tools'))
from validate_gomi import validate
b=json.loads((repo/'data/gomi-support.json').read_text());c=json.loads((O/'candidate.json').read_text());n=json.loads((O/'new-cities.json').read_text());old=json.loads((O/'accepted-content.json').read_text())
assert c['cities'][:21]==b['cities'];assert c['sources'][:len(b['sources'])]==b['sources']
assert len(c['cities'])==21+len(n['cities'])
assert n['sources']==old['sources']
assert (n['draft'],n['not_for_publication'],n['human_reviewed'])==(True,True,False)
for city in n['cities']:
 for service in city['services']:
  assert service['review_status']=='ai_reviewed' and service['ai_reviewed_at']=='2026-10-18' and service['human_reviewed_at'] is None
assert not validate(c,repo)
assert validate(c,repo,publication=True)
for nc,oc in zip(n['cities'],old['cities']):
 for ns,os in zip(nc['services'],oc['services']):assert ns['fields']==os['fields'] and ns['questions_for_office']==os['questions_for_office']
fields=0;sources=0;qs=0
for city in c['cities']:
 pref,slug=city['id'].split(':');soup=BeautifulSoup((O/f'preview/{pref}-gomi-support/{slug}.html').read_text(),'html.parser')
 for service in city['services']:
  card=soup.find(id='route-'+service['id']);assert card
  for key,f in service['fields'].items():
   node=card.select_one('[data-field="'+key+'"]');assert node
   expected=' '.join(service['id']+'--'+s for s in f['source_ids']);assert node['data-source-ids']==expected
   def strings(v):
    if isinstance(v,str):yield v
    elif isinstance(v,dict):
     for x in v.values():yield from strings(x)
    elif isinstance(v,list):
     for x in v:yield from strings(x)
   for value in strings(f['value']):assert ''.join(value.split()) in ''.join(node.get_text(' ',strip=True).split()),(city['id'],key,value)
   fields+=1
  for sid in {sid for f in service['fields'].values() for sid in f['source_ids']}:
   src=next(s for s in c['sources'] if s['id']==sid);node=card.find(id='source-'+service['id']+'--'+sid);assert node['data-checked']==src['checked'];assert node['data-updated']==(src['source_updated'] or '');assert node.find('a')['href']==src['url'];sources+=1
  for q in service.get('questions_for_office',[]):assert q in card.get_text(' ',strip=True);qs+=1
result=dict(schema_errors=[],publication_gate_rejected=True,baseline_cities_preserved=len(b['cities']),baseline_sources_preserved=len(b['sources']),fields_preserved=fields,service_sources_dates_preserved=sources,questions_preserved=qs,accepted_content_facts_unchanged=True,accepted_content_sources_unchanged=True,accepted_content_questions_unchanged=True,transport_pages_regenerated=0,candidate_sha256=hashlib.sha256((O/'candidate.json').read_bytes()).hexdigest(),new_sha256=hashlib.sha256((O/'new-cities.json').read_bytes()).hexdigest())
(O/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
