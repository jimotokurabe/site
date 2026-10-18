"""Accept only independently reviewed and hash-pinned B04 packets."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
review = json.loads((OUT / 'review/review-b04.json').read_text())
assert review['field_count'] == 40 and review['service_count'] == 4
assert review['recheck']['remaining_required_findings'] == []
for entry in review['recheck']['current_candidates']:
    packet = OUT / entry['city'] / 'new-city.json'
    assert hashlib.sha256(packet.read_bytes()).hexdigest() == entry['sha256'], entry['city']
(OUT / 'accepted-content.json').write_bytes((OUT / 'new-cities.json').read_bytes())
for filename in ('new-cities.json', 'candidate.json'):
    path = OUT / filename
    data = json.loads(path.read_text())
    for city in data['cities']:
        if city['id'] != 'okayama:okayama':
            continue
        for service in city['services']:
            service.update(review_status='ai_reviewed', ai_reviewed_at='2026-10-18',
                           human_reviewed_at=None,
                           review_scope_note='B04岡山初稿40項目の独立AI原典照合と必須指摘修正後の差分再検査。新潟は保留。版・原典位置はreview/review-b04.json。人手・窓口確認ではない。')
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
