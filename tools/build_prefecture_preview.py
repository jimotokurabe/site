"""県ページだけを再生成し、ローカルで確認する（全市町村の再生成は不要）。"""
from pathlib import Path
import argparse,json,shutil
from bs4 import BeautifulSoup
import build as b
from prefecture_navigation import render_prefecture

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--pref',nargs='+',help='県ID。省略時は設定済みのすべての県')
    ap.add_argument('--out',default=str(b.ROOT/'preview'))
    args=ap.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    registry=json.loads((b.ROOT/'data/prefecture-navigation.json').read_text())
    selected=args.pref or list(registry)
    if any(pid not in registry for pid in selected):ap.error('案内図の設定がない県です')
    for name in ['index.html','about.html','privacy.html','menkyo-henno-guide.html','site.css','notice.css','home.css']:
        shutil.copy(b.ROOT/name,out/name)
    for pid in selected:
        dirname=b.guide_dir(b.load_pref(b.ROOT/'data'/f'{pid}-menkyo-henno.json')['pref'])
        shutil.copytree(b.ROOT/dirname,out/dirname,dirs_exist_ok=True)
    for f in out.rglob('*.html'):
        soup=BeautifulSoup(f.read_text(),'html.parser')
        for script in soup.select('script'):
            if 'gtag' in str(script) or 'googletagmanager' in script.get('src',''):script.decompose()
        if not soup.select_one('meta[name=robots]'):
            soup.head.append(soup.new_tag('meta',attrs={'name':'robots','content':'noindex'}))
        f.write_text(str(soup))
    for pid in selected:render_prefecture(pid,out,draft=True)
    print('生成した県:',', '.join(selected))

if __name__=='__main__':main()
