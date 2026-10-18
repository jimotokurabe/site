"""Combine only independently accepted B05 packets. Never publish."""
from pathlib import Path
import json,hashlib,copy
O=Path(__file__).resolve().parent;R=O.parents[1];B=R/'gomi-expansion-b05/data/gomi-support.json'
assert hashlib.sha256(B.read_bytes()).hexdigest()=='0e2b15a7558f0a9774d5f478b8d5b532e8c43238a6407243425da4f773c35c4d'
b=json.loads(B.read_text());selection=json.loads((O/'selection.json').read_text());n=dict(schema_version=b['schema_version'],checked='2026-10-18',human_reviewed=False,draft=True,not_for_publication=True,cities=[],sources=[]);inputs=[]
for item in selection['accepted']:
 p=O/item['slug']/'new-city.json';assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'];d=json.loads(p.read_text());assert d['draft'] and d['not_for_publication'];n['cities']+=d['cities'];n['sources']+=d['sources'];inputs.append(item)
assert n['cities']
(O/'accepted-content.json').write_text(json.dumps(n,ensure_ascii=False,indent=2)+'\n')
for c in n['cities']:
 for s in c['services']:s.update(review_status='ai_reviewed',ai_reviewed_at='2026-10-18',human_reviewed_at=None,review_scope_note='B05の独立AI原典照合と修正差分確認。範囲・原典位置・対象hashはselection.jsonと各review記録。人手原文確認ではない。')
c=copy.deepcopy(b);c.pop('publication_approval',None);c.update(draft=True,not_for_publication=True,human_reviewed=False,review_note='公開24地域を保持。新規B05は限定AIレビュー、公開承認なし。')
for key in ('cities','sources'):
 ids=[x['id'] for x in c[key]+n[key]];assert len(ids)==len(set(ids)),key;c[key]+=n[key]
for name,d in [('candidate.json',c),('new-cities.json',n)]: (O/name).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
(O/'generation-input.json').write_text(json.dumps({'base_sha256':hashlib.sha256(B.read_bytes()).hexdigest(),'inputs':inputs,'published_count':24},ensure_ascii=False,indent=2)+'\n');print(len(c['cities']),'total,',len(n['cities']),'new')
