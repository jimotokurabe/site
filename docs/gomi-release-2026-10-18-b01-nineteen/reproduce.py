"""Reproduce owner-approved data; read-only by default, --write explicitly installs it."""
from pathlib import Path
import argparse,copy,hashlib,json,sys
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def reproduce():
 plan=json.loads((HERE/'plan.json').read_text());approval=json.loads((HERE/'owner-approval.json').read_text())
 for name,digest in plan['inputs'].items():assert sha(HERE/name)==digest,name
 assert sha(HERE/'base-data.json')==plan['base_data_sha256']
 assert sha(HERE/'inputs/candidate.json')==plan['candidate_sha256']==approval['reviewed_candidate_sha256']
 assert approval['status']=='approved' and approval['by']=='site_owner' and approval['accepts_ai_reviewed_pilot'] is True
 assert approval['city_ids']==plan['new_city_ids']
 base=json.loads((HERE/'base-data.json').read_text());data=json.loads((HERE/'inputs/candidate.json').read_text());original=copy.deepcopy(data)
 assert data['cities'][:17]==base['cities'] and data['sources'][:104]==base['sources']
 assert [c['id'] for c in data['cities']]==plan['existing_city_ids']+plan['new_city_ids']
 sys.path.insert(0,str(REPO/'tools'));from validate_gomi import validate
 assert not validate(data,REPO);assert validate(data,REPO,publication=True)
 data.update(draft=False,not_for_publication=False,review_note=plan['release_review_note'])
 data['publication_approval']={**approval,'city_ids':plan['existing_city_ids']+plan['new_city_ids'],'new_city_ids':plan['new_city_ids'],'prior_approval':base['publication_approval'],'review_plan_sha256':sha(HERE/'plan.json')}
 for city in data['cities']:
  if city['id'] in plan['new_city_ids']:city['publication_status']='approved'
 assert not validate(data,REPO,publication=True),validate(data,REPO,publication=True)
 for old,new in zip(original['cities'],data['cities']):
  adjusted=copy.deepcopy(new);adjusted['publication_status']=old['publication_status'];assert adjusted==old
 assert data['sources']==original['sources'] and data['human_reviewed'] is False
 return (json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');a=p.parse_args();payload=reproduce();target=REPO/'data/gomi-support.json'
 if a.write:target.write_bytes(payload)
 assert target.read_bytes()==payload
 print('OK: approved release data reproduced byte-for-byte; candidate and all review inputs hash-verified')
