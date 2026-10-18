#!/usr/bin/env python3
"""Validate research data for the municipal waste-support preview."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

DEFAULT_DATA = Path(__file__).resolve().parents[1] / "data" / "gomi-support.json"
KINDS = {"regular_bulky", "self_dropoff", "daily_support", "bulky_carry_support"}
EVIDENCE = {"official_listing", "searched_not_found"}
REVIEW_STATES = {"explicit", "explicit_exclusion", "not_stated", "not_found", "conflicting", "needs_confirmation"}
REQUIRED_FIELDS = {
    "waste_scope", "collection_location", "indoor_carry", "eligibility", "family_help",
    "fees", "limits", "application", "attendance", "contact",
}
CITY_ID = re.compile(r"^([a-z0-9-]+):([a-z0-9-]+)$")


def _iso_date(value: Any) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True  # False and 0 can be intentional, explicit facts.


def _validate_conditions(value, path, errors):
    if isinstance(value, dict):
        allowed = {'label', 'all', 'any', 'exception', 'exclusion', 'note'}
        if not set(value) <= allowed or not any(key in value for key in allowed - {'label'}):
            errors.append(f"{path}: unknown or empty condition group")
        for key, child in value.items():
            if key in {'all', 'any'} and (not isinstance(child, list) or not child):
                errors.append(f"{path}.{key}: expected non-empty condition list")
            if key == 'label' and (not isinstance(child, str) or not child.strip()):
                errors.append(f"{path}.label: expected non-empty heading")
            _validate_conditions(child, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_conditions(child, f"{path}[{index}]", errors)
    elif not isinstance(value, (str, bool, int, float)) and value is not None:
        errors.append(f"{path}: unsupported condition value")


def _validate_questions(value, path, errors):
    if not isinstance(value, list) or any(not isinstance(q, str) or not q.strip() for q in value):
        errors.append(f"{path}: expected a list of non-empty questions")


def _known_city_ids(root: Path) -> set[str]:
    """Read source regional master records from data/*-menkyo-henno.json."""
    known: set[str] = set()
    for path in (root / "data").glob("*-menkyo-henno.json"):
        try:
            master = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        pref = master.get("pref", {}).get("id") if isinstance(master, dict) else None
        entries = master.get("cities") if isinstance(master, dict) else None
        if not isinstance(pref, str) or not isinstance(entries, list):
            continue
        for entry in entries:
            slug = entry.get("slug") if isinstance(entry, dict) else None
            if isinstance(slug, str) and slug:
                known.add(f"{pref}:{slug}")
    return known


def validate(data: dict[str, Any], root: str | Path | None = None, publication: bool = False) -> list[str]:
    """Return validation errors; publication=True additionally enforces scoped owner approval and a recorded review."""
    errors: list[str] = []
    project_root = Path(root) if root else DEFAULT_DATA.parents[1]
    if not isinstance(data, dict):
        return ["root: expected an object"]
    cities = data.get("cities")
    sources = data.get("sources")
    if not _iso_date(data.get("checked")):
        errors.append("checked: expected a real YYYY-MM-DD date")
    if not isinstance(cities, list) or not cities:
        errors.append("cities: expected a non-empty list")
        cities = []
    if not isinstance(sources, list) or not sources:
        errors.append("sources: expected a non-empty list")
        sources = []

    approval = data.get("publication_approval", {})
    if not isinstance(approval, dict):
        approval = {}
    if publication and (approval.get("status") != "approved" or approval.get("by") != "site_owner" or not _iso_date(approval.get("approved_at"))):
        errors.append("publication_approval: explicit site-owner approval and date required")
    source_by_id: dict[str, dict[str, Any]] = {}
    for i, src in enumerate(sources):
        path = f"sources[{i}]"
        if not isinstance(src, dict):
            errors.append(f"{path}: expected an object")
            continue
        sid = src.get("id")
        if not isinstance(sid, str) or not sid.strip():
            errors.append(f"{path}.id: required")
        elif sid in source_by_id:
            errors.append(f"{path}.id: duplicate {sid}")
        else:
            source_by_id[sid] = src
        url = src.get("url")
        hostname = (urlsplit(url).hostname or "").lower().rstrip(".") if isinstance(url, str) else ""
        official_host = hostname.endswith((".lg.jp", ".go.jp")) or hostname in {"lg.jp", "go.jp", "www.nishi.or.jp", "nishi.or.jp"}
        # Municipal joint waste facility linked from Inagawa's official guidance.
        if sid in {'kunisaki-handcarried', 'kawanishi-kunisaki'} and url == 'https://www.kunisakicc.jp/association/kcc/hand-carried/':
            owners = {c.get('id') for c in cities if isinstance(c, dict)
                      for service in c.get('services', [])
                      for fact in service.get('fields', {}).values()
                      if sid in fact.get('source_ids', [])}
            official_host = owners == ({'hyogo:inagawa'} if sid == 'kunisaki-handcarried' else {'hyogo:kawanishi'})
        if hostname == 'www.city.amagasaki.hyogo.jp' or (sid == 'amagasaki-faq287' and url == 'https://faq.city.amagasaki.hyogo.jp/faq/detail.aspx?id=287'):
            owners = {c.get('id') for c in cities if isinstance(c, dict)
                      for service in c.get('services', [])
                      for fact in service.get('fields', {}).values()
                      if sid in fact.get('source_ids', [])}
            official_host = owners == {'hyogo:amagasaki'}
        # Kawasaki uses .jp, including its city-linked bulky-waste reception FAQ.
        # Permit only this municipality; this is provenance, not publication approval.
        if hostname == 'www.city.kawasaki.jp' or (sid == 'kawasaki-dropoff-faq' and url == 'https://www.sodai.city.kawasaki.jp/eco/view/kawasaki/faq.html'):
            owners = {c.get('id') for c in cities if isinstance(c, dict)
                      for service in c.get('services', [])
                      for fact in service.get('fields', {}).values()
                      if sid in fact.get('source_ids', [])}
            official_host = owners == {'kanagawa:kawasaki'}
        # These municipal sites use .jp rather than the common .lg.jp domain.
        # Accept them only when the source is referenced exclusively by that city.
        municipal_hosts = {
            'www.city.chigasaki.kanagawa.jp': 'kanagawa:chigasaki',
            'www.city.fujisawa.kanagawa.jp': 'kanagawa:fujisawa',
            'www.city.sagamihara.kanagawa.jp': 'kanagawa:sagamihara',
            'www.city.yokosuka.kanagawa.jp': 'kanagawa:yokosuka',
            'www.city.itabashi.tokyo.jp': 'tokyo:itabashi',
            'www.city.nerima.tokyo.jp': 'tokyo:nerima',
            'www.city.ota.tokyo.jp': 'tokyo:ota',
            'www.city.suginami.tokyo.jp': 'tokyo:suginami',
            'www.city.suita.osaka.jp': 'osaka:suita',
            'www.city.takatsuki.osaka.jp': 'osaka:takatsuki',
            'www.city.toyonaka.osaka.jp': 'osaka:toyonaka',
            'www.city.sapporo.jp': 'hokkaido:sapporo',
            'www.city.chiba.jp': 'chiba:chiba',
            'www.city.okayama.jp': 'okayama:okayama',
            'www.city.nagoya.jp': 'aichi:nagoya',
            'www.city.sendai.jp': 'miyagi:sendai',
            'www.city.takarazuka.hyogo.jp': 'hyogo:takarazuka',
            'www.city.kawanishi.hyogo.jp': 'hyogo:kawanishi',
        }
        # Itami links its joint municipal facility hosted by Toyonaka.
        if sid in {'itami-cleanland', 'itami-cleanland-net'} and url in {
            'https://www.city.toyonaka.osaka.jp/kurashi/gomi_risaikuru_bika/cleanland/mochikomi/tel/mochikomi.html',
            'https://www.city.toyonaka.osaka.jp/kurashi/gomi_risaikuru_bika/cleanland/mochikomi/net/rinnjigomi.html',
        }:
            owners = {c.get('id') for c in cities if isinstance(c, dict)
                      for service in c.get('services', [])
                      for fact in service.get('fields', {}).values()
                      if sid in fact.get('source_ids', [])}
            official_host = owners == {'hyogo:itami'}
        if hostname in municipal_hosts and not official_host:
            owners = {c.get('id') for c in cities if isinstance(c, dict)
                      for service in c.get('services', [])
                      for fact in service.get('fields', {}).values()
                      if sid in fact.get('source_ids', [])}
            official_host = owners == {municipal_hosts[hostname]}
        if not isinstance(url, str) or urlsplit(url).scheme not in {"http", "https"} or not official_host:
            errors.append(f"{path}.url: expected an official municipal/prefectural government hostname")
        if src.get("source_kind") != "official":
            errors.append(f"{path}.source_kind: expected official")
        if not _nonempty(src.get("title")):
            errors.append(f"{path}.title: required")
        if not _iso_date(src.get("checked")):
            errors.append(f"{path}.checked: expected a real YYYY-MM-DD date")
        if src.get("source_updated") is not None and not _iso_date(src.get("source_updated")):
            errors.append(f"{path}.source_updated: expected null or a real YYYY-MM-DD date")

    known_cities = _known_city_ids(project_root)
    if not known_cities:
        errors.append(f"regional master: no municipality records found under {project_root / 'data'}/*-menkyo-henno.json")
    seen_cities: set[str] = set()
    seen_services: set[str] = set()
    for ci, city in enumerate(cities):
        cp = f"cities[{ci}]"
        if not isinstance(city, dict):
            errors.append(f"{cp}: expected an object")
            continue
        cid = city.get("id")
        match = CITY_ID.fullmatch(cid) if isinstance(cid, str) else None
        if not match:
            errors.append(f"{cp}.id: expected pref:slug")
        else:
            if cid in seen_cities:
                errors.append(f"{cp}.id: duplicate {cid}")
            seen_cities.add(cid)
            if cid not in known_cities:
                errors.append(f"{cp}.id: {cid} is not in data/*-menkyo-henno.json regional master")
        for key in ("name", "kana", "selection_reason"):
            if not _nonempty(city.get(key)):
                errors.append(f"{cp}.{key}: required")
        if publication and city.get("publication_status") != "approved":
            errors.append(f"{cp}.publication_status: must be approved for publication")
        if publication and cid not in approval.get("city_ids", []):
            errors.append(f"{cp}: city is outside the approved publication scope")
        _validate_questions(city.get("common_questions_for_office", []), f"{cp}.common_questions_for_office", errors)
        services = city.get("services")
        if not isinstance(services, list) or not services:
            errors.append(f"{cp}.services: expected a non-empty list")
            continue
        seen_kinds: dict[str, list[str | None]] = {}
        for si, service in enumerate(services):
            sp = f"{cp}.services[{si}]"
            if not isinstance(service, dict):
                errors.append(f"{sp}: expected an object")
                continue
            service_id = service.get("id")
            if not isinstance(service_id, str) or not service_id.strip():
                errors.append(f"{sp}.id: required")
            elif service_id in seen_services:
                errors.append(f"{sp}.id: duplicate {service_id}")
            else:
                seen_services.add(service_id)
            kind = service.get("kind")
            if not isinstance(kind, str) or kind not in KINDS:
                errors.append(f"{sp}.kind: expected one of {', '.join(sorted(KINDS))}")
            variant = service.get("variant")
            if variant is not None and variant not in ("standard", "pilot"):
                errors.append(f"{sp}.variant: expected standard or pilot")
            if isinstance(kind, str) and kind in KINDS:
                prior = seen_kinds.setdefault(kind, [])
                # A regular programme and a time-limited pilot need separate cards.
                # Unlabelled duplicates and multiple copies of either remain errors.
                if prior and (variant not in ("standard", "pilot") or None in prior or variant in prior):
                    errors.append(f"{sp}.kind: duplicate {kind} in city without distinct standard/pilot variants")
                prior.append(variant)
            if not _nonempty(service.get("name")):
                errors.append(f"{sp}.name: required")
            evidence_status = service.get("evidence_status")
            if not isinstance(evidence_status, str) or evidence_status not in EVIDENCE:
                errors.append(f"{sp}.evidence_status: unknown evidence state")
            if not _iso_date(service.get("checked")):
                errors.append(f"{sp}.checked: expected a real YYYY-MM-DD date")
            if publication:
                review_status = service.get("review_status")
                date_key = {"human_reviewed": "human_reviewed_at", "ai_reviewed": "ai_reviewed_at"}.get(review_status)
                if not date_key or not _iso_date(service.get(date_key)):
                    errors.append(f"{sp}: recorded review status and date required for publication")
                if review_status == "ai_reviewed" and approval.get("accepts_ai_reviewed_pilot") is not True:
                    errors.append(f"{sp}: AI-reviewed pilot needs explicit owner publication approval")
            _validate_questions(service.get("questions_for_office", []), f"{sp}.questions_for_office", errors)
            fields = service.get("fields")
            if not isinstance(fields, dict):
                errors.append(f"{sp}.fields: expected an object")
                continue
            for field_name in REQUIRED_FIELDS:
                fp = f"{sp}.fields.{field_name}"
                fact = fields.get(field_name)
                if not isinstance(fact, dict):
                    errors.append(f"{fp}: required field object")
                    continue
                state = fact.get("state")
                value = fact.get("value")
                _validate_conditions(value, fp + ".value", errors)
                if not isinstance(state, str) or state not in REVIEW_STATES:
                    errors.append(f"{fp}.state: unknown evidence state")
                if state in {"explicit", "explicit_exclusion"} and not _nonempty(value):
                    errors.append(f"{fp}.value: explicit facts need a non-empty value")
                # Some research records keep a short explanation of what remains
                # unknown (for example, the doorway details were not stated).
                # That is useful evidence context; never allow a boolean/number to
                # turn an unresolved state into an accidental exclusion or zero.
                if state in {"not_stated", "not_found"} and value is not None and not isinstance(value, str):
                    errors.append(f"{fp}.value: unresolved fact must be null or explanatory text")
                refs = fact.get("source_ids")
                if not isinstance(refs, list) or not refs:
                    errors.append(f"{fp}.source_ids: at least one source reference required")
                else:
                    for ref in refs:
                        if not isinstance(ref, str) or ref not in source_by_id:
                            errors.append(f"{fp}.source_ids: unresolved source {ref!r}")
                links = fact.get("links", [])
                if not isinstance(links, list):
                    errors.append(f"{fp}.links: expected a list")
                else:
                    for link in links:
                        if not isinstance(link, dict) or not isinstance(link.get('source_id'), str) or link['source_id'] not in source_by_id or not _nonempty(link.get('label')):
                            errors.append(f"{fp}.links: expected a labeled official source reference")
                        elif not isinstance(refs, list) or link['source_id'] not in refs:
                            errors.append(f"{fp}.links: contact source must also be included in source_ids")
                if state == "explicit_exclusion" and value is not False and not _nonempty(value):
                    errors.append(f"{fp}: explicit exclusion needs a stated value")
    if publication:
        for key, expected in (("draft", False), ("not_for_publication", False)):
            if data.get(key) is not expected:
                errors.append(f"{key}: must be {str(expected).lower()} for publication")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="JSON dataset (default: data/gomi-support.json)")
    parser.add_argument("--publication", action="store_true", help="also require scoped owner publication approval and recorded review")
    args = parser.parse_args()
    try:
        data = json.loads(args.data.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read {args.data}: {exc}")
        return 2
    errors = validate(data, root=args.data.resolve().parents[1], publication=args.publication)
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors))
        return 1
    print(f"OK: {args.data} ({'publication gate' if args.publication else 'review schema'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
