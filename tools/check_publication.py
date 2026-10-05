"""Verify nationwide public navigation, indexing and local links before publication."""
from pathlib import Path
from urllib.parse import urlsplit, unquote
from collections import Counter
import json,re,sys,xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT
paths=json.loads((OUT/'enriched-pages.json').read_text())
issues=[];page_info={};local_links=[]
for f in OUT.rglob('*.html'):
 if '.git' in f.parts or 'preview' in f.relative_to(OUT).parts:continue
 s=BeautifulSoup(f.read_text(),'html.parser')
 ids=[e['id'] for e in s.select('[id]')]
 if len(ids)!=len(set(ids)):issues.append([str(f.relative_to(OUT)),'duplicate ids'])
 page_info[f.resolve()]={'ids':set(ids),'h1':len(s.select('h1')),'noindex':bool(s.select_one('meta[name="robots"][content*="noindex"]')),'draft':bool(s.select_one('.draft')),'canonical':s.select_one('link[rel="canonical"]')['href'] if s.select_one('link[rel="canonical"]') else None,'crumb':str(s.select_one('.crumbs')),'analytics':'G-T1PQ72Q40S' in str(s),'hrefs':{a['href'] for a in s.select('a[href]')}}
 for a in s.select('[href],[src]'):
  href=a.get('href',a.get('src',''));u=urlsplit(href)
  if u.scheme or href.startswith('//'):continue
  target=(OUT/unquote(u.path.lstrip('/'))) if u.path.startswith('/') else (f.parent/unquote(u.path)) if u.path else f
  if target.is_dir():target=target/'index.html'
  local_links.append((f.resolve(),target.resolve(),unquote(u.fragment),href))
for f,t,fragment,href in local_links:
 if not t.exists():issues.append([str(f.relative_to(OUT)),'missing local target',href])
 elif fragment and t in page_info and fragment not in page_info[t]['ids']:issues.append([str(f.relative_to(OUT)),'missing anchor',href])
home=(OUT/'index.html').read_text();cities=json.loads(re.search(r'const cities=(.*?);const input=',home).group(1))
assert len(paths)==len(cities)==1741
assert {c['url'] for c in cities}==set(paths.values())
sitemap={n.text for n in ET.parse(OUT/'sitemap.xml').findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')}
for key,path in paths.items():
 p=page_info[(OUT/path).resolve()];pid=key.split(':')[0];pref=pid+'-menkyo-henno.html'
 if p['h1']!=1 or p['noindex'] or p['draft'] or not p['analytics']:issues.append([key,'public page metadata'])
 if p['canonical']!='https://jimotokurabe.jp/'+path or p['canonical'] not in sitemap:issues.append([key,'canonical/sitemap'])
 if '../'+pref not in p['crumb'] or 'href="../"' not in p['crumb']:issues.append([key,'breadcrumb'])
 if path not in page_info[(OUT/pref).resolve()]['hrefs']:issues.append([key,'prefecture navigation'])
for pid in {k.split(':')[0] for k in paths}:
 pref=pid+'-menkyo-henno.html';p=page_info[(OUT/pref).resolve()]
 if pref not in page_info[(OUT/'index.html').resolve()]['hrefs'] or p['noindex'] or p['draft']:issues.append([pid,'public prefecture'])
assert (OUT/'CNAME').read_text().strip()=='jimotokurabe.jp' and (OUT/'.nojekyll').exists()
assert 'Allow: /' in (OUT/'robots.txt').read_text()
report={'municipalities':len(paths),'prefectures':47,'public_html_pages':len(page_info),'sitemap_urls':len(sitemap),'issues':issues}
print(json.dumps(report,ensure_ascii=False,indent=2))
sys.exit(bool(issues))
