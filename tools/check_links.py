"""手順ページの外部リンク（出典や申し込み先）が開けるかを確かめる。

使い方: python3 tools/check_links.py hyogo-menkyo-henno/kawanishi.html
開けないリンクがあれば、終了コード1で終わる。
"""
import html
import re
import subprocess
import sys
import time

SKIP = ("https://jimotokurabe.jp/", "https://line.me/")


def status(url):
    # 役所のサイトは一時的につながらないことがあるので、3回まで試す
    for i in range(3):
        r = subprocess.run(
            ["curl", "-sS", "-L", "-o", "/dev/null", "-m", "30", "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
             "-w", "%{http_code}", url],
            capture_output=True, text=True)
        code = r.stdout.strip()
        if code.startswith(("2", "3")) or i == 2:
            break
        time.sleep(3 * (i + 1))
    return code if code not in ("", "000") else "ERR " + r.stderr.strip()[:80]


def main():
    text = open(sys.argv[1], encoding="utf-8").read()
    urls = sorted({html.unescape(u) for u in re.findall(r'<a [^>]*href="(https?://[^"]+)"', text)})
    bad = 0
    for u in urls:
        if u.startswith(SKIP):
            continue
        s = status(u)
        ok = s.startswith(("2", "3"))
        bad += not ok
        print(("OK " if ok else "NG ") + s, u)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
