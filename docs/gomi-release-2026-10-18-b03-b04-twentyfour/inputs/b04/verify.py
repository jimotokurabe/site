"""Verify B04 preview facts, citations, and the unchanged B03 baseline."""
import hashlib
import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
REPO = ROOT / 'gomi-expansion-b03'
sys.path.insert(0, str(REPO / 'tools'))
from validate_gomi import validate

base = json.loads((ROOT / '調査/2026-10-18_ごみ支援拡大B03/candidate.json').read_text())
public = json.loads((REPO / 'data/gomi-support.json').read_text())
candidate = json.loads((OUT / 'candidate.json').read_text())
addition = json.loads((OUT / 'new-cities.json').read_text())
accepted = json.loads((OUT / 'accepted-content.json').read_text())
review = json.loads((OUT / 'review/review-b04.json').read_text())

assert candidate['cities'][:23] == base['cities']
assert candidate['sources'][:len(base['sources'])] == base['sources']
assert base['cities'][:21] == public['cities']
assert base['sources'][:len(public['sources'])] == public['sources']
assert len(candidate['cities']) == 24 and len(addition['cities']) == 1
assert candidate['cities'][23:] == addition['cities']
assert candidate['sources'][len(base['sources']):] == addition['sources']
assert addition['sources'] == accepted['sources']
assert (addition['draft'], addition['not_for_publication'], addition['human_reviewed']) == (True, True, False)
assert review['recheck']['remaining_required_findings'] == []
for current, original in zip(addition['cities'], accepted['cities']):
    for service, original_service in zip(current['services'], original['services']):
        assert service['review_status'] == 'ai_reviewed'
        assert service['ai_reviewed_at'] == '2026-10-18'
        assert service['human_reviewed_at'] is None
        assert service['fields'] == original_service['fields']
        assert service['questions_for_office'] == original_service['questions_for_office']

errors = validate(candidate, REPO)
assert not errors, errors
assert validate(candidate, REPO, publication=True), 'publication gate unexpectedly passed'


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


source_by_id = {source['id']: source for source in candidate['sources']}
fields = citations = questions = 0
for city in candidate['cities']:
    pref, slug = city['id'].split(':')
    path = OUT / f'preview/{pref}-gomi-support/{slug}.html'
    soup = BeautifulSoup(path.read_text(), 'html.parser')
    for service in city['services']:
        card = soup.find(id='route-' + service['id'])
        assert card, (city['id'], service['id'])
        for key, fact in service['fields'].items():
            node = card.select_one('[data-field="' + key + '"]')
            assert node, (city['id'], service['id'], key)
            assert node['data-source-ids'] == ' '.join(service['id'] + '--' + sid for sid in fact['source_ids'])
            visible = ''.join(node.get_text(' ', strip=True).split())
            for value in strings(fact['value']):
                assert ''.join(value.split()) in visible, (city['id'], service['id'], key, value)
            fields += 1
        for sid in {sid for fact in service['fields'].values() for sid in fact['source_ids']}:
            source = source_by_id[sid]
            node = card.find(id='source-' + service['id'] + '--' + sid)
            assert node['data-checked'] == source['checked']
            assert node['data-updated'] == (source['source_updated'] or '')
            assert node.find('a')['href'] == source['url']
            citations += 1
        for question in service.get('questions_for_office', []):
            assert question in card.get_text(' ', strip=True)
            questions += 1

result = {
    'schema_errors': [], 'publication_gate_rejected': True,
    'previous_preview_cities_preserved': 23,
    'previous_preview_sources_preserved': len(base['sources']),
    'published_cities_preserved': 21,
    'published_sources_preserved': len(public['sources']),
    'fields_preserved': fields, 'service_sources_dates_preserved': citations,
    'questions_preserved': questions,
    'accepted_content_facts_unchanged': True,
    'accepted_content_sources_unchanged': True,
    'accepted_content_questions_unchanged': True,
    'transport_pages_regenerated': 0,
    'candidate_sha256': hashlib.sha256((OUT / 'candidate.json').read_bytes()).hexdigest(),
    'new_sha256': hashlib.sha256((OUT / 'new-cities.json').read_bytes()).hexdigest(),
}
(OUT / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False))
