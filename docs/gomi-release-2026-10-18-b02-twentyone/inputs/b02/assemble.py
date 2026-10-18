"""Combine separately researched packets, preserving the 19-city public baseline."""
import copy, hashlib, json
from pathlib import Path
O=Path(__file__).resolve().parent
R=O.parents[1];BASE=R/'gomi-expansion-b02/data/gomi-support.json'
BASE_HASH='4ffb84a0e0a61aec2a0d3f3632d3d25306cc6a18b4d47899813c1e2719de9eb2'
assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_HASH
b=json.loads(BASE.read_text());n=dict(schema_version=b['schema_version'],checked='2026-10-18',human_reviewed=False,draft=True,not_for_publication=True,cities=[],sources=[])
inputs=[]
for slug in ('kyoto','hiroshima'):
 p=O/slug/'new-city.json'
 if not p.exists():continue
 x=json.loads(p.read_text());assert x['not_for_publication'] and x['draft']
 n['cities']+=x['cities'];n['sources']+=x['sources'];inputs.append({'path':str(p.relative_to(O)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
assert n['cities'],'No prepared municipalities'
for key in ('cities','sources'):
 ids=[x['id'] for x in b[key]+n[key]];assert len(ids)==len(set(ids)),key
c=copy.deepcopy(b);c.pop('publication_approval',None);c.update(draft=True,not_for_publication=True,human_reviewed=False,review_note='既存19地域の累積AI検査を保持。新規経路の範囲と版は今回review記録参照。公開承認なし。')
for key in ('cities','sources'):c[key]+=n[key]
for name,x in [('candidate.json',c),('new-cities.json',n)]: (O/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
(O/'generation-input.json').write_text(json.dumps({'base':str(BASE),'base_sha256':BASE_HASH,'inputs':inputs,'new_city_ids':[x['id'] for x in n['cities']],'published_count':19},ensure_ascii=False,indent=2)+'\n')
print('new',len(n['cities']),'total',len(c['cities']))
