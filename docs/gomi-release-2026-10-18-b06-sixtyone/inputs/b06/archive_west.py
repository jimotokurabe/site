"""Fetch official West-group evidence into immutable raw/text files."""
from __future__ import annotations
import concurrent.futures
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
FOLDER = {"kagawa":"takamatsu", "ehime":"matsuyama", "okinawa":"naha"}
URLS = {
    "yamaguchi": {
        "daily": "https://www.city.yamaguchi.lg.jp/soshiki/52/108820.html",
        "regular": "https://www.city.yamaguchi.lg.jp/soshiki/52/60387.html",
        "dropoff": "https://www.city.yamaguchi.lg.jp/site/gomisigen/161801.html",
    },
    "tokushima": {
        "daily": "https://www.city.tokushima.tokushima.jp/kurashi/recycle/gomi/hureai.html",
        "regular": "https://www.city.tokushima.tokushima.jp/kurashi/recycle/gomi/sodaigomi.html",
        "dropoff": "https://www.city.tokushima.tokushima.jp/kurashi/recycle/gomi/jigyou/hannyuu.html",
    },
    "kagawa": {
        "daily": "https://www.city.takamatsu.kagawa.jp/smph/kurashi/kurashi/gomi/oshirase/recycl_up20240409.html",
        "regular": "https://www.city.takamatsu.kagawa.jp/smph/kurashi/kurashi/gomi/rinjisodai/dashikata.html",
        "dropoff": "https://www.city.takamatsu.kagawa.jp/smph/kurashi/kurashi/gomi/mochikomi/moushikomi.html",
    },
    "ehime": {
        "daily": "https://www.city.matsuyama.ehime.jp/kurashi/gomi/dashikata/seisou.html",
        "regular": "https://www.city.matsuyama.ehime.jp/kurashi/gomi/dashikata/sodaigomi_dashikata.html",
        "dropoff": "https://www.city.matsuyama.ehime.jp/kurashi/gomi/dashikata/kateigomi.html",
    },
    "kochi": {
        "daily": "https://www.city.kochi.kochi.jp/soshiki/64/fureaishuushuu.html",
        "regular": "https://www.city.kochi.kochi.jp/soshiki/64/gomi1-kanenfunen01.html",
        "dropoff": "https://www.city.kochi.kochi.jp/soshiki/66/motikomi-02.html",
        "family-dropoff": "https://faq.city.kochi.kochi.jp/faq/detail.aspx?id=1422",
    },
    "saga": {
        "regular": "https://www.city.saga.lg.jp/kurashi/seikatsukankyo/1/1/5/3840.html",
        "carry": "https://www.city.saga.lg.jp/kurashi/seikatsukankyo/1/1/5/3841.html",
        "dropoff": "https://www.city.saga.lg.jp/kurashi/seikatsukankyo/1/3/1667.html",
    },
    "nagasaki": {
        "daily": "https://www.city.nagasaki.lg.jp/page/2575.html",
        "regular": "https://www.city.nagasaki.lg.jp/page/3031.html",
        "dropoff": "https://www.city.nagasaki.lg.jp/page/4091.html",
    },
    "kumamoto": {
        "daily": "https://www.city.kumamoto.jp/kankyo/kiji0031428/index.html",
        "regular": "https://www.city.kumamoto.jp/kiji003552/index.html",
        "dropoff": "https://www.city.kumamoto.jp/kankyo/kiji00322037/index.html",
    },
    "oita": {
        "daily": "https://www.city.oita.oita.jp/o150/gomidashishien2021.html",
        "regular": "https://www.city.oita.oita.jp/o150/kurashi/gomi/1263438599187.html",
        "dropoff": "https://www.city.oita.oita.jp/o017/homepage/bulkygarbage.html",
    },
    "miyazaki": {
        "daily": "https://www.city.miyazaki.miyazaki.jp/life/trash/collection_point/39752.html",
        "regular": "https://www.city.miyazaki.miyazaki.jp/life/trash/fractionation/34204.html",
        "dropoff": "https://www.city.miyazaki.miyazaki.jp/life/trash/bring/405845.html",
    },
    "kagoshima": {
        "daily": "https://www.city.kagoshima.lg.jp/seisojimusyo/magokorosyusyu.html",
        "regular": "https://www.city.kagoshima.lg.jp/shigenseisaku/gomi/kate/dashikata/wakekata/sodaigomi.html",
        "dropoff": "https://www.city.kagoshima.lg.jp/shigenseisaku/gomi/kate/dashikata/wakekata/sodaigomi.html",
    },
    "okinawa": {
        "daily": "https://www.city.naha.okinawa.jp/_res/projects/default_project/_page_/001/003/020/5torikumi.pdf",
        "regular": "https://www.city.naha.okinawa.jp/kurasitetuduki/gomi-recycling/1001934/1007525/1001941.html",
        "dropoff": "https://www.city.naha.okinawa.jp/kurasitetuduki/gomi-recycling/1001934/1007547/1001949.html",
    },
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(item):
    slug, key, url = item
    folder = ROOT / FOLDER.get(slug, slug) / "official"
    folder.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0 (evidence archive)"})
    response.raise_for_status()
    raw = response.content
    is_pdf = "pdf" in response.headers.get("Content-Type", "") or urlparse(url).path.lower().endswith(".pdf")
    raw_file = folder / (key + (".pdf" if is_pdf else ".html.source"))
    raw_file.write_bytes(raw)
    if is_pdf:
        import subprocess
        text_content = subprocess.check_output(["pdftotext", "-layout", str(raw_file), "-"]).decode("utf-8", "replace")
        title = key
    else:
        soup = BeautifulSoup(raw, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else key
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text_content = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
    text_file = folder / (key + ".txt")
    text_file.write_text(text_content, encoding="utf-8")
    updated = re.search(r"(?:最終)?更新日[：:\s]*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日|[0-9]{4}/[0-9]{1,2}/[0-9]{1,2}|令和[0-9]{1,2}年[0-9]{1,2}月[0-9]{1,2}日)", text_content[:5000])
    return slug, key, {
        "id": f"{slug}-{key}", "url": url, "title": title,
        "source_kind": "official", "checked": "2026-10-18",
        "source_updated": updated.group(1) if updated else None,
        "http_status": response.status_code, "final_url": response.url,
        "retrieved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "content_type": response.headers.get("Content-Type"),
        "raw_file": str(raw_file.relative_to(ROOT)),
        "text_file": str(text_file.relative_to(ROOT)),
        "raw_sha256": sha(raw), "text_sha256": sha(text_content.encode("utf-8")),
        "last_modified_header": response.headers.get("Last-Modified"),
    }


if __name__ == "__main__":
    unique = []
    seen = set()
    for slug, mapping in URLS.items():
        for key, url in mapping.items():
            if (slug, url) not in seen:
                unique.append((slug, key, url))
                seen.add((slug, url))
    results = {slug: [] for slug in URLS}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(fetch, item): item for item in unique}
        for future in concurrent.futures.as_completed(futures):
            try:
                slug, key, record = future.result()
                results[slug].append(record)
                print(slug, key, record["http_status"], flush=True)
            except Exception as exc:
                print("ERROR", futures[future], repr(exc), flush=True)
    for slug, records in results.items():
        (ROOT / FOLDER.get(slug, slug) / "official-metadata.json").write_text(
            json.dumps(sorted(records, key=lambda x: x["id"]), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
