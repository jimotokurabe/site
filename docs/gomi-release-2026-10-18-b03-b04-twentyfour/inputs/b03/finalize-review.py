"""Run after assemble.py; accept only the independently reviewed packet hashes."""
from pathlib import Path
import json,hashlib
O=Path(__file__).resolve().parent
r=json.loads((O/'review/review-b03.json').read_text())
assert not r['recheck']['remaining_required_findings']
for x in r['recheck']['current_candidates']:
 assert hashlib.sha256((O/x['city']/'new-city.json').read_bytes()).hexdigest()==x['sha256']
(O/'accepted-content.json').write_bytes((O/'new-cities.json').read_bytes())
for name in ('new-cities.json','candidate.json'):
 p=O/name;d=json.loads(p.read_text())
 for c in d['cities']:
  if c['id'] not in ('chiba:chiba','saitama:saitama'):continue
  for s in c['services']:
   s.update(review_status='ai_reviewed',ai_reviewed_at='2026-10-18',human_reviewed_at=None,review_scope_note='B03初稿80項目の独立AI原典照合と必須6指摘修正後の差分再検査。対象版と原典位置はreview/review-b03.json。人手確認・窓口確認ではない。')
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
