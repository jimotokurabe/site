"""調べたときの抜き書きが、いまの公式ページに本当に載っているかを確かめる。

使い方: python3 tools/check_quotes.py <抜き書きのファイル.json>
抜き書きのファイルは、次の形のリスト（リポジトリの外に置く。公開しないため）:
  [{"slug": "sakai", "part": "henno", "url": "https://...", "quote": "原文の短い抜き書き"}, ...]
空白・改行・全角半角のちがいは無視して比べる。PDF は pdftotext があれば読む。
見つからない抜き書きがあれば、終了コード1で終わる。
"""
import html
import json
import re
import subprocess
import sys
import tempfile
import unicodedata

CACHE = {}


def norm(s):
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"\s+", "", s)


def page_text(url):
    if url in CACHE:
        return CACHE[url]
    with tempfile.NamedTemporaryFile(suffix=".bin") as f:
        r = subprocess.run(["curl", "-sS", "-L", "-m", "40", "-A", "Mozilla/5.0", "-o", f.name,
                            "-w", "%{http_code} %{content_type}", url], capture_output=True, text=True)
        code, _, ctype = r.stdout.partition(" ")
        if not code.startswith("2"):
            CACHE[url] = None, f"開けない（{code or r.stderr.strip()[:60]}）"
            return CACHE[url]
        raw = open(f.name, "rb").read()
        if "pdf" in ctype or url.lower().endswith(".pdf"):
            p = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True)
            if p.returncode:
                CACHE[url] = None, "PDF を読めない（pdftotext がない）"
                return CACHE[url]
            text = p.stdout
        else:
            m = re.search(rb'charset=["\']?([\w-]+)', raw[:3000], re.I)
            enc = (m.group(1).decode() if m else "utf-8").lower().replace("shift_jis", "cp932").replace("sjis", "cp932")
            doc = raw.decode(enc, errors="replace")
            doc = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", doc)
            text = html.unescape(re.sub(r"<[^>]+>", "", doc))
    CACHE[url] = norm(text), ""
    return CACHE[url]


def main():
    notes = json.load(open(sys.argv[1], encoding="utf-8"))
    bad = 0
    for n in notes:
        text, why = page_text(n["url"])
        ok = text is not None and norm(n["quote"]) in text
        if not ok:
            bad += 1
            print(f"NG  {n['slug']:<14} {n.get('part', ''):<6} {why or '抜き書きが見つからない'}  {n['url']}\n    「{n['quote']}」")
    print(f"{len(notes) - bad}/{len(notes)} 件の抜き書きを、いまの公式ページで確かめました。")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
