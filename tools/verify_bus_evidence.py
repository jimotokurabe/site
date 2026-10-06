"""非公開の抜き書きを全文一致で照合し、本文を調査フォルダにキャッシュする。

python3 tools/verify_bus_evidence.py /path/to/notes.json --cache /private/cache
リポジトリに本文・抜き書き・調査キャッシュを保存しない。
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re

from check_quotes import norm, page_text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('notes')
    ap.add_argument('--cache', required=True)
    ap.add_argument('--refresh', action='store_true')
    ap.add_argument('--ocr', help='画像PDFの読み取り結果（非公開JSON: {url,pages:[{page,text}]} またはその配列）')
    args = ap.parse_args()
    cache = Path(args.cache).resolve()
    root = Path(__file__).resolve().parent.parent
    assert root not in [cache, *cache.parents], 'cache must be outside the public repository'
    cache.mkdir(parents=True, exist_ok=True)
    notes = json.loads(Path(args.notes).read_text(encoding='utf-8'))
    urls = sorted({n['url'] for n in notes})
    ocr = json.loads(Path(args.ocr).read_text(encoding='utf-8')) if args.ocr else None
    ocr_sources = {row['url']: row for row in (ocr if isinstance(ocr, list) else [ocr])} if ocr else {}

    def fetch(url):
        path = cache / (hashlib.sha256(url.encode()).hexdigest() + '.json')
        if path.exists() and not args.refresh:
            row = json.loads(path.read_text(encoding='utf-8'))
        else:
            text, error = page_text(url)
            row = {'url': url, 'text': text, 'error': error}
        if not row['error'] and url in ocr_sources:
            pages = ocr_sources[url]['pages']
            # 見本の文字層だけがある画像PDFも、目視したページのOCRで照合する。
            # 元の抽出本文は残し、manual_pdf を付けた引用だけ指定ページを使う。
            row.update(ocr_pages=pages, method='OCR assisted: macOS Vision')
            if not row['text']:
                row['text'] = norm('\n'.join(p['text'] for p in pages))
        path.write_text(json.dumps(row, ensure_ascii=False), encoding='utf-8')
        return row

    with ThreadPoolExecutor(max_workers=6) as pool:
        sources = {row['url']: row for row in pool.map(fetch, urls)}
    failures = []
    for n in notes:
        source = sources[n['url']]
        text = source['text']
        if n.get('manual_pdf') and source.get('ocr_pages') and 'page' in n:
            text = norm('\n'.join(p['text'] for p in source['ocr_pages'] if p['page'] == n['page']))
        # 空白で単語に分解しない。省略記号のある引用は各連続部分を照合する。
        fragments = [norm(q) for q in re.split(r'[|…]', n['quote']) if norm(q)]
        if not text or not fragments or not all(q in text for q in fragments):
            failures.append({'slug': n['slug'], 'url': n['url'], 'quote': n['quote'],
                             'reason': sources[n['url']]['error'] or 'exact normalized quote not found'})
    result = {'sources': len(urls), 'quotes': len(notes), 'passed': len(notes) - len(failures), 'failures': failures}
    (cache / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(bool(failures))


if __name__ == '__main__':
    main()
