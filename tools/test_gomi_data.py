"""Mutation checks for the gomi dataset validator; run with python3 -m unittest."""

import copy
import json
import unittest
from pathlib import Path

from validate_gomi import validate

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data/gomi-support.json").read_text(encoding="utf-8"))


class GomiValidationTests(unittest.TestCase):
    def test_current_research_schema_passes(self):
        self.assertEqual(validate(DATA, root=ROOT), [])

    def test_explicit_false_exclusion_is_valid(self):
        data = copy.deepcopy(DATA)
        field = data["cities"][0]["services"][0]["fields"]["indoor_carry"]
        field.update(value=False, state="explicit_exclusion")
        self.assertEqual(validate(data, root=ROOT), [])

    def test_unresolved_value_cannot_be_converted_to_false(self):
        data = copy.deepcopy(DATA)
        field = data["cities"][0]["services"][0]["fields"]["eligibility"]
        field.update(value=False, state="not_stated")
        self.assertTrue(any("unresolved fact must be null or explanatory text" in e for e in validate(data, root=ROOT)))

    def test_missing_source_reference_fails(self):
        data = copy.deepcopy(DATA)
        data["cities"][0]["services"][0]["fields"]["fees"]["source_ids"] = ["missing"]
        self.assertTrue(any("unresolved source" in e for e in validate(data, root=ROOT)))

    def test_duplicate_service_id_fails(self):
        data = copy.deepcopy(DATA)
        data["cities"][0]["services"][1]["id"] = data["cities"][0]["services"][0]["id"]
        self.assertTrue(any("duplicate" in e and ".id:" in e for e in validate(data, root=ROOT)))

    def test_unknown_city_id_fails(self):
        data = copy.deepcopy(DATA)
        data["cities"][0]["id"] = "hyogo:not-a-city"
        self.assertTrue(any("not in data/*-menkyo-henno.json" in e for e in validate(data, root=ROOT)))

    def test_malformed_kind_and_source_ref_return_errors(self):
        data = copy.deepcopy(DATA)
        service = data["cities"][0]["services"][0]
        service["kind"] = []
        service["fields"]["fees"]["source_ids"] = [{}]
        errors = validate(data, root=ROOT)
        self.assertTrue(any(".kind: expected one of" in e for e in errors))
        self.assertTrue(any("unresolved source" in e for e in errors))

    def test_needs_confirmation_is_a_supported_state(self):
        data = copy.deepcopy(DATA)
        field = data["cities"][0]["services"][0]["fields"]["fees"]
        field.update(value="金額を窓口確認中", state="needs_confirmation")
        self.assertFalse(any("fees.state: unknown" in e for e in validate(data, root=ROOT)))

    def test_untrusted_hostname_fails(self):
        data = copy.deepcopy(DATA)
        data["sources"][0]["url"] = "https://city.gov.example/gomi"
        self.assertTrue(any("expected an official municipal/prefectural government hostname" in e for e in validate(data, root=ROOT)))

    def test_publication_gate_rejects_unreviewed_draft(self):
        data = copy.deepcopy(DATA)
        data.update(draft=True, not_for_publication=True)
        data.pop('publication_approval', None)
        for city in data['cities']:
            for service in city['services']:
                service['review_status'] = 'ai_draft'
        errors = validate(data, root=ROOT, publication=True)
        self.assertTrue(any("draft: must be false" in e for e in errors))
        self.assertTrue(any("publication_approval:" in e for e in errors))
        self.assertTrue(any("recorded review status and date required" in e for e in errors))

    def test_approval_does_not_cover_future_cities(self):
        data = copy.deepcopy(DATA)
        data['publication_approval']['city_ids'] = []
        self.assertTrue(any('outside the approved' in e for e in validate(data, root=ROOT, publication=True)))

    def test_bare_url_is_validation_error(self):
        data = copy.deepcopy(DATA)
        data['sources'][0]['url'] = 'bad-url'
        self.assertTrue(any('.url:' in e for e in validate(data, root=ROOT)))


if __name__ == "__main__":
    unittest.main()
