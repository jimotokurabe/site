"""設定済み県の所属・図・短文・リンク・公開設定を検査する。"""
from pathlib import Path
from collections import Counter
import argparse,json,re
from bs4 import BeautifulSoup
import build as b

def check(pid,out,draft=False):
    cfg=json.loads((b.ROOT/'data/prefecture-navigation.json').read_text())[pid]
    data=b.load_pref(b.ROOT/'data'/f'{pid}-menkyo-henno.json');cities=data['cities'];regions=data['regions']
    issues=[];rids={r['id'] for r in regions};slugs={c['slug'] for c in cities}
    if set(cfg['shapes'])!=rids or cfg['default_region'] not in rids:issues.append('地域設定の不一致')
    if len(slugs)!=len(cities) or any(c['r'] not in rids for c in cities):issues.append('市町村の重複・所属不一致')
    box=[float(x) for x in cfg.get('viewBox','0 0 480 525').split()]
    for rid,shape in cfg['shapes'].items():
        if len(shape)!=3 or not isinstance(shape[0],str) or not re.match(r'^\s*M',shape[0]):issues.append([rid,'図の書式'])
        elif not (box[0]<=shape[1]<=box[0]+box[2] and box[1]<=shape[2]<=box[1]+box[3]-21):issues.append([rid,'ラベル位置'])
    for slug,text in cfg.get('summaries',{}).items():
        if slug not in slugs or not isinstance(text,str) or not 0<len(text)<=95:issues.append([slug,'短文設定'])
    file=out/b.list_path(data['pref']);s=BeautifulSoup(file.read_text(),'html.parser')
    rows=s.select('[data-city]')
    if {r['id'] for r in rows}!=slugs or len(rows)!=len(cities):issues.append('生成市町村の不一致')
    if Counter(r['data-city-region'] for r in rows)!=Counter(c['r'] for c in cities):issues.append('生成地域の不一致')
    if len(s.select('g[data-region]'))!=len(regions):issues.append('図の地域数')
    if len(s.select('h1'))!=1:issues.append('H1件数')
    analytics=any('G-T1PQ72Q40S' in str(el) for el in s.select('script'))
    if analytics==draft:issues.append('アクセス解析設定')
    if not s.select_one('link[rel=stylesheet][href="prefecture-region.css"]'):issues.append('地域図スタイル欠落')
    if bool(s.select_one('meta[name=robots][content*=noindex]'))!=draft:issues.append('検索設定')
    if s.select_one('link[rel=canonical]')['href']!=b.SITE+file.name:issues.append('正規URL')
    for row in rows:
        if not (out/row.a['href']).exists():issues.append([row['id'],'個別ページ欠落'])
        if not row.p.get_text(strip=True):issues.append([row['id'],'紹介文欠落'])
    ids=[e['id'] for e in s.select('[id]')]
    if len(ids)!=len(set(ids)):issues.append('重複ID')
    return {'pref':pid,'municipalities':len(cities),'regions':len(regions),'issues':issues}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',default=str(b.ROOT));ap.add_argument('--pref',nargs='+');ap.add_argument('--draft',action='store_true');args=ap.parse_args()
    pids=args.pref or list(json.loads((b.ROOT/'data/prefecture-navigation.json').read_text()))
    reports=[check(pid,Path(args.out),args.draft) for pid in pids]
    print(json.dumps(reports,ensure_ascii=False,indent=2))
    raise SystemExit(any(r['issues'] for r in reports))
if __name__=='__main__':main()
