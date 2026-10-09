"""Check the structural safety of an unpublished nationwide warm preview.

Usage: python3 tools/check_warm_preview.py --root . --out preview
The source tree is read only; the output directory must already be built.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

BASE = "https://jimotokurabe.jp/"
ASSETS = ("family-guide.webp", "warm-shared.css", "warm-experience.js")


def fail(issues: list[list[str]], page: str, message: str) -> None:
    issues.append([page, message])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="repository source root")
    parser.add_argument("--out", type=Path, required=True, help="already-built preview root")
    args = parser.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    issues: list[list[str]] = []

    try:
        manifest = json.loads((root / "data/municipality-supplements.json").read_text(encoding="utf-8"))["municipalities"]
        cities = {row["key"] for row in manifest}
    except (OSError, KeyError, ValueError, TypeError) as exc:
        print(json.dumps({"error": f"cannot read municipality manifest: {exc}"}, ensure_ascii=False, indent=2))
        return 2
    prefs = {key.split(":", 1)[0] for key in cities if ":" in key}
    if len(cities) != 1741 or len(prefs) != 47:
        fail(issues, "manifest", f"expected 1741 unique cities/47 prefectures; got {len(cities)}/{len(prefs)}")

    expected: dict[str, str] = {"index.html": BASE}
    for pid in sorted(prefs):
        expected[f"{pid}-menkyo-henno.html"] = BASE + f"{pid}-menkyo-henno.html"
    for key in sorted(cities):
        pid, slug = key.split(":", 1)
        rel = f"{pid}-menkyo-henno/{slug}.html"
        expected[rel] = BASE + rel

    existing: dict[Path, BeautifulSoup] = {}
    for rel, canonical_url in expected.items():
        page = out / rel
        if not page.is_file():
            fail(issues, rel, "expected preview HTML is missing")
            continue
        soup = BeautifulSoup(page.read_text(encoding="utf-8"), "html.parser")
        existing[page.resolve()] = soup
        robots = [m.get("content", "").lower() for m in soup.select('meta[name="robots"],meta[name="googlebot"]')]
        if not any("noindex" in value for value in robots):
            fail(issues, rel, "missing noindex")
        canonical = soup.select_one('link[rel="canonical"]')
        if not canonical or canonical.get("href") != canonical_url:
            fail(issues, rel, f"canonical should be {canonical_url}")
        if len(soup.select("h1")) != 1:
            fail(issues, rel, "expected exactly one h1")
        raw = page.read_text(encoding="utf-8")
        if re.search(r"#/city|TOWN_IMAGE", raw, flags=re.I):
            fail(issues, rel, "demo city hash or TOWN_IMAGE marker found")
        for image in soup.select("img[src]"):
            src = image["src"]
            if Path(urlsplit(src).path).name != "family-guide.webp":
                fail(issues, rel, f"unexpected city-specific or other image: {src}")

    for asset in ASSETS:
        if not (out / "assets" / asset).is_file():
            fail(issues, f"assets/{asset}", "required shared family asset is missing")

    # Confirm every generated page loads the shared family styles and behavior.
    nav_paths = ["index.html", *(f"{pid}-menkyo-henno.html" for pid in sorted(prefs))]
    city_paths = [f"{key.replace(':', '-menkyo-henno/')}.html" for key in sorted(cities)]
    for rel in [*nav_paths, *city_paths]:
        soup = existing.get((out / rel).resolve())
        if soup is None:
            continue
        for tag, attr, asset in (("link", "href", "warm-shared.css"), ("script", "src", "warm-experience.js")):
            if not any(Path(urlsplit(t.get(attr, "")).path).name == asset for t in soup.find_all(tag)):
                fail(issues, rel, f"missing link to {asset}")
    home = existing.get((out / "index.html").resolve())
    if home and not any(Path(urlsplit(t.get("src", "")).path).name == "family-guide.webp" for t in home.select("img[src]")):
        fail(issues, "index.html", "missing link to family-guide.webp")

    # Internal page links and embedded resources must resolve within the preview.
    # External official and existing-public links are intentionally left external.
    anchors = {path: {node.get("id") for node in soup.select("[id]")} | {node.get("name") for node in soup.select("a[name]")} for path, soup in existing.items()}
    for page, soup in existing.items():
        rel = page.relative_to(out).as_posix()
        for tag in soup.select("a[href],link[href],script[src],img[src]"):
            value = tag.get("href", tag.get("src", ""))
            parsed = urlsplit(value)
            if parsed.scheme or value.startswith("//"):
                continue
            path = unquote(parsed.path)
            if not path:
                target = page
            elif path.startswith("/"):
                target = out / path.lstrip("/")
            else:
                target = page.parent / path
            if target.is_dir():
                target /= "index.html"
            if not target.exists():
                fail(issues, rel, f"missing local link/resource: {value}")
            elif parsed.fragment and target.suffix == ".html" and target.resolve() in anchors and unquote(parsed.fragment) not in anchors[target.resolve()]:
                fail(issues, rel, f"missing local link anchor: {value}")

    print(json.dumps({"municipalities": len(cities), "prefectures": len(prefs), "expected_html": len(expected), "checked_html": len(existing), "issues": issues}, ensure_ascii=False, indent=2))
    return bool(issues)


if __name__ == "__main__":
    raise SystemExit(main())
