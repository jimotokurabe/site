#!/usr/bin/env python3
"""Hash-pinned release preparation. Default is read-only; never deploys or edits repo."""
import argparse, copy, hashlib, json, pathlib, subprocess, sys
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
REPO = ROOT / 'gomi-release-preview'
PLAN = json.loads((HERE / 'plan.json').read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
    ap = argparse.ArgumentParser()
    ap.add_argument('--approval', type=pathlib.Path)
    ap.add_argument('--out', type=pathlib.Path)
    args = ap.parse_args()
    candidate = ROOT / PLAN['candidate']['path']
    assert sha(candidate) == PLAN['candidate']['sha256'], 'Candidate changed: re-review and re-approval required'
    head = subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip()
    assert head == PLAN['pre_release_head'], 'HEAD changed: rebase preservation check required'
    data = json.loads(candidate.read_text())
    base = json.loads((REPO / 'data/gomi-support.json').read_text())
    assert sha(REPO / 'data/gomi-support.json') == PLAN['base_data_sha256'], 'Published data changed'
    city_by_id = {c['id']:c for c in data['cities']}
    assert set(city_by_id) == set(PLAN['existing_city_ids'] + PLAN['new_city_ids'])
    assert all(city_by_id[c['id']] == c for c in base['cities']), 'Existing city changed'
    sources = {s['id']:s for s in data['sources']}
    assert all(sources[s['id']] == s for s in base['sources']), 'Existing source changed'
    for review in PLAN['review_files']:
        assert sha(ROOT / review['path']) == review['sha256'], 'Review version changed: ' + review['path']
    sys.path.insert(0, str(REPO / 'tools'))
    from validate_gomi import validate
    assert not validate(data, REPO), validate(data, REPO)
    assert validate(data, REPO, publication=True), 'Candidate must remain publication-blocked'
    if not args.approval:
        assert not args.out, '--out requires real operator approval'
        print(json.dumps({'status':'dry_run_ok_awaiting_owner_approval','candidate_sha256':sha(candidate),
                          'existing_cities_unchanged':8,'new_cities':7,'fields':600,
                          'national_pages_regenerated':0,'publication_gate':'blocked_as_expected'},ensure_ascii=False))
        return
    assert args.out, '--out is required with approval'
    approval = json.loads(args.approval.read_text())
    assert approval['status'] == 'approved' and approval['by'] == 'site_owner'
    assert approval['reviewed_candidate_sha256'] == PLAN['candidate']['sha256']
    assert set(approval['city_ids']) == set(PLAN['new_city_ids']), 'Approval must match the exact seven new cities'
    assert approval.get('accepts_ai_reviewed_pilot') is True
    assert isinstance(approval.get('basis'),str) and approval['basis'].strip(), 'Record actual owner instruction'
    from datetime import date
    date.fromisoformat(approval['approved_at'])
    out = args.out.resolve()
    assert out != REPO and REPO not in out.parents, 'Output must stay outside repository'
    assert not out.exists(), 'Refuse overwrite'
    release = copy.deepcopy(data)
    release['draft'] = False
    release['not_for_publication'] = False
    release['review_note'] = PLAN['release_review_note']
    prior = base['publication_approval']
    release['publication_approval'] = {**approval,'city_ids':PLAN['existing_city_ids'] + PLAN['new_city_ids'],
        'prior_approval':prior,'new_city_ids':PLAN['new_city_ids'],
        'review_plan_sha256':sha(HERE / 'plan.json')}
    for city in release['cities']:
        if city['id'] in PLAN['new_city_ids']:
            city['publication_status'] = 'approved'
            for service in city['services']:
                service['review_status'] = 'ai_reviewed'
                service['ai_reviewed_at'] = '2026-10-16'
    assert not validate(release, REPO, publication=True), validate(release, REPO, publication=True)
    assert all({s['id']:s for s in release['sources']}[s['id']] == s for s in data['sources'])
    for old,new in zip(data['cities'],release['cities']):
        stripped = copy.deepcopy(new)
        stripped['publication_status'] = old['publication_status']
        for a,b in zip(old['services'],stripped['services']):
            for key in ('review_status','ai_reviewed_at'):
                if key in a: b[key]=a[key]
                else: b.pop(key,None)
        assert stripped == old, 'Only approval/review metadata may change'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'prepared_outside_repo_not_published','path':str(out),'sha256':sha(out)},ensure_ascii=False))
if __name__ == '__main__':
    try: run()
    except (AssertionError,KeyError,ValueError) as error: sys.exit(str(error))
