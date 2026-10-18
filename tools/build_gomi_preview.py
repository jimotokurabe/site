"""Local preview only; never a publication builder. Generate only waste pages.
Existing site files provide read-only local links.

python3 tools/build_gomi_preview.py --data candidate.json --out preview
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from bs4 import BeautifulSoup
from gomi_pages import generate_pages
from validate_gomi import validate

ROOT=Path(__file__).resolve().parents[1]

def safe_write_target(out, target):
    """Reject symlinks in every write path, including existing parent folders."""
    for part in [target, *target.parents]:
        if part.is_symlink():
            raise ValueError('Refuse write through symlink: ' + str(part))
        if part == out:
            break
    if not target.resolve().is_relative_to(out):
        raise ValueError('Write escapes preview: ' + str(target))

def replace_home_entry(raw, replacement):
    # Locate the original bytes: HTML reserialization changes attribute order.
    from html.parser import HTMLParser
    class EntryParser(HTMLParser):
        def __init__(self):
            super().__init__(); self.depth = 0; self.start = None; self.spans = []
            self.lines = raw.splitlines(keepends=True)
        def source_position(self):
            line, column = self.getpos()
            return sum(map(len, self.lines[:line - 1])) + column
        def handle_starttag(self, tag, attrs):
            if tag == 'section':
                if dict(attrs).get('id') == 'gomi-support-entry':
                    if self.start is not None: raise ValueError('Nested duplicate entry')
                    self.start = self.source_position(); self.depth = 1
                elif self.start is not None: self.depth += 1
        def handle_endtag(self, tag):
            if tag == 'section' and self.start is not None:
                self.depth -= 1
                if self.depth == 0:
                    end = raw.index('>', self.source_position()) + 1
                    self.spans.append((self.start, end)); self.start = None
    parser = EntryParser(); parser.feed(raw)
    if len(parser.spans) != 1 or parser.start is not None:
        raise ValueError('Home waste entry must occur exactly once')
    start, end = parser.spans[0]
    return raw[:start] + replacement + raw[end:]

def build(data_path, out, base=ROOT):
    data_path=Path(data_path).resolve();out=Path(out).absolute();base=Path(base).resolve()
    if any(p.is_symlink() for p in [out,*out.parents]):
        raise ValueError('Output or ancestor is a symlink')
    out=out.resolve()
    if out==ROOT or out==base or ROOT in out.parents:
        raise ValueError('Output must be outside repository and base; refuse public overwrite')
    data=json.loads(data_path.read_text())
    errors=validate(data,root=ROOT)
    if errors: raise ValueError('; '.join(errors))
    pages=generate_pages(data,draft=True)
    out.mkdir(parents=True,exist_ok=True)
    # Link existing directories/files instead of rebuilding 1,741 transport pages.
    for item in base.iterdir():
        if item.name.startswith('.') or item.name in ('tools','data','docs','assets') or item.name in pages:
            continue
        if item.is_dir() and item.name.endswith('-gomi-support'): continue
        target=out/item.name
        if not target.exists() and not target.is_symlink(): target.symlink_to(item,target_is_directory=item.is_dir())
    assets=out/'assets';safe_write_target(out,assets);assets.mkdir(exist_ok=True)
    for item in (ROOT/'assets').iterdir():
        target=assets/item.name
        if item.is_file():
            safe_write_target(out,target)
            shutil.copy2(item,target)
    for relative, html in pages.items():
        target=out/relative;safe_write_target(out,target);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(html)
    # Replace the read-only base home link with a local copy before updating the
    # waste entrance. Preserve every byte outside that one existing block.
    from gomi_integration import home_entry
    home=out/'index.html'
    if home.is_symlink(): home.unlink()
    safe_write_target(out,home)
    raw=(base/'index.html').read_text()
    home.write_text(replace_home_entry(raw,home_entry(data)))
    errors=[]
    for relative,html in pages.items():
        soup=BeautifulSoup(html,'html.parser')
        if not soup.select_one('meta[name="robots"][content*="noindex"]'):errors.append(relative+': noindex missing')
        for node in soup.select('[href], [src]'):
            from urllib.parse import urlsplit,unquote
            u=urlsplit(node.get('href',node.get('src','')))
            if u.scheme or u.netloc: continue
            target=out/unquote(u.path.lstrip('/')) if u.path.startswith('/') else (out/relative).parent/unquote(u.path) if u.path else out/relative
            if target.is_dir():target=target/'index.html'
            if not target.exists():errors.append(relative+': missing '+str(u.path))
            elif u.fragment and target.suffix=='.html' and not BeautifulSoup(target.read_text(),'html.parser').find(id=unquote(u.fragment)):
                errors.append(relative+': missing fragment '+u.fragment)
    manifest={'data':str(data_path),'data_sha256':hashlib.sha256(data_path.read_bytes()).hexdigest(),'generated_pages':len(pages),'transport_pages_regenerated':0,'existing_links_base':str(base),'draft':True,'errors':errors,'home_waste_entry_updated':True,'home_preview_sha256':hashlib.sha256(home.read_bytes()).hexdigest(),'outputs':{p:hashlib.sha256((out/p).read_bytes()).hexdigest() for p in pages}}
    safe_write_target(out,out/'generation-manifest.json')
    (out/'generation-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    if errors:raise ValueError(str(errors))
    print(json.dumps({k:v for k,v in manifest.items() if k!='outputs'},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--out',required=True);p.add_argument('--base',default=str(ROOT));a=p.parse_args();build(a.data,a.out,a.base)
