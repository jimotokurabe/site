"""Add the accepted Okayama packet to the unchanged 23-city B03 preview."""
import copy
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
BASE = ROOT / '調査/2026-10-18_ごみ支援拡大B03/candidate.json'
BASE_SHA256 = '32e91f467b0d35538309b4b411a6c2d41b611deca88215db282eb27ebf8bb8a3'

assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA256, 'B03 candidate changed'
base = json.loads(BASE.read_text())
assert len(base['cities']) == 23 and len(base['sources']) == 147
addition = {
    'schema_version': base['schema_version'], 'checked': '2026-10-18',
    'human_reviewed': False, 'draft': True, 'not_for_publication': True,
    'cities': [], 'sources': [],
}
inputs = []
for slug in ('okayama',):
    packet = OUT / slug / 'new-city.json'
    data = json.loads(packet.read_text())
    assert data['draft'] and data['not_for_publication'] and not data['human_reviewed']
    assert len(data['cities']) == 1 and data['cities'][0]['id'] == f'{slug}:{slug}'
    addition['cities'].extend(data['cities'])
    addition['sources'].extend(data['sources'])
    inputs.append({'path': str(packet.relative_to(OUT)), 'sha256': hashlib.sha256(packet.read_bytes()).hexdigest()})
assert len(addition['cities']) == 1
candidate = copy.deepcopy(base)
candidate.pop('publication_approval', None)
candidate.update(draft=True, not_for_publication=True, human_reviewed=False,
                 review_note='既存B03の23地域を保持。B04岡山の原典照合範囲と版はreview記録参照。新潟は保留。公開承認なし。')
for key in ('cities', 'sources'):
    identifiers = [item['id'] for item in candidate[key] + addition[key]]
    assert len(identifiers) == len(set(identifiers)), f'duplicate {key} ID'
    candidate[key].extend(addition[key])
for filename, payload in [('new-cities.json', addition), ('candidate.json', candidate)]:
    (OUT / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
(OUT / 'generation-input.json').write_text(json.dumps({
    'base': str(BASE.relative_to(ROOT)), 'base_sha256': BASE_SHA256,
    'inputs': inputs, 'new_city_ids': [c['id'] for c in addition['cities']],
    'published_count': 21, 'previous_preview_count': 23,
}, ensure_ascii=False, indent=2) + '\n')
print(f"B04 candidate: {len(candidate['cities'])} cities, {len(candidate['sources'])} sources")
