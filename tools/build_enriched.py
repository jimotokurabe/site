"""Build nationwide municipality pages from repository-local audited data."""
from pathlib import Path
import json, sys, shutil, subprocess, re
from bs4 import BeautifulSoup
import build as b
ROOT=b.ROOT
OUT=ROOT/'preview'
DATA=ROOT/'data/municipality-supplements.json'
def load(p):return json.loads(p.read_text())
def facts(items):
 return '<dl class="notice-rows">'+''.join(f'<div><dt>{b.e(k)}</dt><dd>{b.e(str(v).replace('service_area','利用地域').replace('eligibility','対象条件').replace('booking','予約・申込').replace('operating_days','運行日').replace('fare','費用').replace('構造化欄なし（本文確認後に補完）','詳細を追加確認').replace('構造化欄が不足（本文内の記載は要確認）','詳細を追加確認'))}</dd></div>' for k,v in items if v)+'</dl>'
def source(url,label='公式ページで確認'):
 return f'<p><a href="{b.e(url)}" target="_blank" rel="noopener">{label} ↗</a></p>' if url else ''
def topic_label(topic):
 return {'transport':'移動手段','mobility':'地域の交通案内','return':'免許返納の支援','return_support':'免許返納の支援','license_return_support':'免許返納の支援','taxi':'タクシーの助成・利用案内','senior_taxi_support':'高齢者のタクシー助成','electric_bicycle_subsidy':'電動自転車の購入助成','bus_fare_support':'バス運賃の助成','bus_fare_discount':'バス運賃の割引','transport_support':'交通費・外出の支援','mobility_support':'移動・外出の支援','support':'外出・交通費の支援'}.get(topic,topic)
def render(out=None,draft=True,base_built=False):
 global OUT
 OUT=Path(out) if out else ROOT/'preview'
 OUT.mkdir(exist_ok=True,parents=True)
 if not base_built:
  subprocess.run([sys.executable,str(ROOT/'tools/build.py'),'--out',str(OUT),*(['--draft'] if draft else [])],check=True,stdout=subprocess.DEVNULL)
  return
 prefs={d['pref']['id']:d for d in [b.load_pref(f) for f in (ROOT/'data').glob('*-menkyo-henno.json')]}
 mobility={}
 for m in load(ROOT/'data/municipal-mobility.json')['cities']:mobility.setdefault((m['pref'],m['municipality']),[]).append(m)
 east=load(ROOT/'data/east-harima-mobility.json')
 em={m['id']:m for m in east['cities']}
 for entry in load(ROOT/'data/mobility-coverage.json')['entries']:
  m={**em[entry['city']],**entry,'checked':east['checked']};mobility.setdefault((entry['pref'],entry['municipality']),[]).append(m)
 dataset=load(DATA)
 evidence=dataset['records']
 rows=dataset['municipalities']
 assert len(rows)==len({r['key'] for r in rows}), 'municipality overlap'
 paths={};by_pref={}
 for row in rows:
  pid,slug=row['key'].split(':');d=prefs[pid];c=next(c for c in d['cities'] if c['slug']==slug);t=d['taxi'][slug]
  path=f'{b.guide_dir(d["pref"])}/{slug}.html';paths[row['key']]=path;by_pref.setdefault(pid,[]).append((row,path))
  if c.get('guide'):
   soup=BeautifulSoup(b.city_page(c,d,draft),'html.parser');main=soup.select_one('main');old=main.select_one('section.mobility')
   if old:old.decompose()
   crumb=main.select_one('.crumbs')
   if crumb:crumb.clear();crumb.append(BeautifulSoup(f'<a href="../">トップ</a> ＞ <a href="../{b.list_path(d["pref"])}">{b.e(d["pref"]["name"])}</a> ＞ {b.e(c["n"])}','html.parser'))
   h=main.select_one('h1');h.string=c['n']+'の免許返納特典・交通費助成・移動手段'
   ans=main.select_one('section.answer')
   if ans:ans['id']='benefit'
  else:
   text=f'<nav class="crumbs"><a href="../">トップ</a> ＞ <a href="../{b.list_path(d["pref"])}">{b.e(d["pref"]["name"])}</a> ＞ {b.e(c["n"])}</nav><h1>{b.e(c["n"])}の特典・助成・移動手段</h1><section id="benefit"><h2>免許返納の情報</h2><p>{b.e(c["what"])}</p>'+facts([(label,c.get(key)) for key,label in [('age','対象'),('amt','支援内容'),('dl','期限'),('apply','申請先')]])+source(c.get('url'))+f'<p>既存情報の確認日：{b.e(d["checked"])}</p></section>'
   soup=BeautifulSoup(b.shell(title=c['n']+'の特典・助成・移動手段｜じもとくらべ',description=c['what'],path=path,main=text,draft=draft,base='../',page_class='guide'),'html.parser');main=soup.select_one('main')
  menu=BeautifulSoup('<nav class="local-menu" aria-label="この町の情報"><a href="#benefit">返納特典</a><a href="#support">交通費の助成</a><a href="#rides">移動手段</a><a href="#audit">今回の確認状況</a></nav>','html.parser')
  hero=main.select_one('.hero') or main.select_one('h1');hero.insert_after(menu)
  support=f'<section id="support" class="city-section"><h2>交通費の助成・支援</h2><article class="notice-sheet"><h3>{b.e(t.get("name","既存のタクシー助成調査"))}</h3><p>{b.e(t.get("what","記載なし"))}</p>'+facts([(label,t.get(key)) for key,label in [('age','対象'),('amt','支援内容'),('how','申請方法'),('henno_link','免許返納との関係')]])+source(t.get('url'))+f'<p>既存情報の確認日：{b.e(t["checked"])}</p></article>'
  rides='<section id="rides" class="city-section"><h2>通院・買い物に使う移動手段</h2>'
  for m in mobility.get((pid,slug),[]):
   note=f'<p>掲載範囲：{b.e(m.get("scope",m["name"]))}。{b.e(m.get("quick_scope",""))} 全交通手段の網羅ではありません。掲載情報の確認日：{b.e(m["checked"])}</p>'
   rides+=note
   for category in ['rides','supports']:
    for item in m.get(category,[]):
     block=f'<article class="notice-sheet"><h3>{b.e(item["name"])}</h3><p>{b.e(item.get("summary",""))}</p>'+facts([(label,item.get(key)) for key,label in [('service_area','利用地域'),('eligibility','対象'),('booking','予約・申込'),('fare','費用'),('operating_days','運行日'),('check','利用前の確認')]])+source(item.get('source'))+'</article>'
     if category=='rides':rides+=block
     else:support+=block
   if not m.get('rides'):rides+='<p>この既存案内は運賃支援のみで、個別の交通手段は未掲載です。</p>'
  if not mobility.get((pid,slug)):rides+='<p>このページでは個別の交通手段をまだ確認できていません。確認状況は下に記載しています。</p>'
  main.append(BeautifulSoup(support+'</section>'+rides+'</section>','html.parser'))
  r=evidence.get(row['key']);audit='<section id="audit" class="city-section"><h2>今回の確認状況</h2>'
  if r:
   audit+=f'<p>確認作業日：{b.e(r.get("checked","未記録"))}。状態：{b.e({'reviewed':'指定項目を確認（全制度の網羅ではありません）','partial':'一部未確認','checked':'出典確認（全項目の確認ではありません）','reviewed_sources':'出典取得・項目確認中','complete':'指定範囲を確認済み','blocked':'保留','hold':'保留','held':'保留','unverified':'未確認','updated':'確認した補完あり'}.get(r.get('status'),r.get('status','未確認')))}</p><p>以下の根拠は今回取得した箇所です。既存記事全体を再確認済みとする意味ではありません。</p>'
   for s in r.get('sources',[]):
    if not isinstance(s,dict):continue
    ev=s.get('evidence');audit+=f'<article class="notice-sheet"><h3>公式情報の確認</h3><p>{b.e('公式原文を取得' if s.get('fetch_status')==200 else '原文を確認できず・再確認が必要')}</p>'
    # Raw retrieval excerpts stay in audit files; do not display navigation or unrelated prose.
    audit+=source(s.get('url'))+'</article>'
   verified_updates=[u for u in r.get('updates',[]) if isinstance(u,dict) and u.get('reviewed') is True and u.get('safety_accepted') is True and u.get('value') and u.get('source') and u.get('evidence')]
   if verified_updates:
    audit+='<h3>今回補完した情報</h3>'
    for u in verified_updates:
     audit+=f'<article class="notice-sheet"><h4>{b.e(str(u.get("topic","確認情報")))}</h4>'+facts([({'service_area':'利用できる地域','eligibility':'対象','booking':'予約・申込','fare':'料金・助成額','operating_days':'運行日','benefit':'特典内容','support':'支援内容','mobility':'移動手段','reservation':'予約方法','operation':'運行・利用地域','operation_status':'運行状況','applicable_modes':'利用できる交通手段','return_support':'返納支援','application':'申請方法','amount':'支援額','check':'利用前の確認'}.get(str(u.get('field')),str(u.get('field','内容'))),u['value'])])+source(u['source'])+'</article>'
   audit+='<h3>残る確認事項</h3><ul>'+''.join(f'<li>{b.e(str(v).replace('service_area','利用地域').replace('eligibility','対象条件').replace('booking','予約・申込').replace('operating_days','運行日').replace('fare','費用').replace('構造化欄なし（本文確認後に補完）','詳細を追加確認').replace('構造化欄が不足（本文内の記載は要確認）','詳細を追加確認'))}</li>' for v in r.get('unresolved',[]))+'</ul>'
  else:audit+='<p>今回の公式再確認は未着手です。既存の掲載情報をご確認ください。</p>'
  main.append(BeautifulSoup(audit+'</section>','html.parser'))
  if r:
   accepted=[u for u in r.get('updates',[]) if isinstance(u,dict) and u.get('reviewed') is True and u.get('safety_accepted') is True and u.get('value') and u.get('source') and u.get('evidence')]
   if accepted:
    if not mobility.get((pid,slug)) and any(re.search(r'運行|バス|タクシー|乗合|停留所|乗車|送迎',u['value']) for u in accepted):
     placeholder=main.select_one('#rides p')
     if placeholder:
      placeholder.clear();placeholder.append(BeautifulSoup('今回確認できた案内は、<a href="#confirmed">下の補足情報</a>をご覧ください。','html.parser'))
    changes=[u for u in accepted if any(word in str(u.get('value','')) for word in ['終了','開始予定','廃止'])]
    if changes:
     note='<aside class="city-section"><h2>利用前に確認したい期限・変更</h2><p>申請や利用の前に、以下の条件と確認日をご確認ください。</p>'+''.join('<p>'+b.e(u['value'])+'</p>'+source(u['source']) for u in changes)+'</aside>'
     main.select_one('.local-menu').insert_after(BeautifulSoup(note,'html.parser'))
    extra='<section id="confirmed" class="city-section"><h2>公式情報で確認した補足</h2><p>確認日：'+b.e(r.get('checked','未記録'))+'</p>'
    grouped={}
    for u in accepted:grouped.setdefault(str(u.get('topic','確認情報')),[]).append(u)
    labels={'service_area':'利用地域','eligibility':'対象','booking':'予約・申込','fare':'料金・助成額','operating_days':'運行日','benefit':'特典内容','support':'支援内容','mobility':'移動手段','reservation':'予約方法','operation':'運行・利用地域','operation_status':'運行状況','applicable_modes':'利用できる交通手段','return_support':'返納支援','application':'申請方法','amount':'支援額'}
    for topic,updates in grouped.items():
     extra+='<article class="notice-sheet"><h3>'+b.e(topic_label(topic))+'</h3>'+facts([(labels.get(u.get('field'),'確認内容'),u['value']) for u in updates])
     for url in dict.fromkeys(u['source'] for u in updates):extra+=source(url)
     extra+='</article>'
    extra+='</section>'
    # Put newly confirmed information beside the transport/support information, ahead of the audit log.
    main.select_one('#audit').insert_before(BeautifulSoup(extra,'html.parser'))
    main.select_one('.local-menu').append(BeautifulSoup('<a href="#confirmed">追加の案内</a>','html.parser'))
    audit_heading=main.select_one('#audit')
    redundant=audit_heading.find('h3',string='今回補完した情報')
    if redundant:
     sibling=redundant.find_next_sibling()
     while sibling and sibling.name!='h3':
      nxt=sibling.find_next_sibling();sibling.decompose();sibling=nxt
     redundant.decompose()
  
  if r and not r.get('unresolved'):
   empty_heading=main.select_one('#audit').find('h3',string='残る確認事項')
   if empty_heading:
    empty_list=empty_heading.find_next_sibling('ul')
    if empty_list:empty_list.decompose()
    empty_heading.decompose()
  # Local previews do not send analytics and keep their own indexing protections.
  if draft:
   for s in soup.select('script'):
    if 'gtag' in str(s) or 'googletagmanager' in s.get('src',''):s.decompose()
  nav=soup.select_one('.site-nav')
  if nav:
   nav.clear();nav.append(BeautifulSoup(f'<a href="../index.html">地域を探す</a><a href="../{b.list_path(d["pref"])}">{b.e(d["pref"]["name"])}の市町村</a>','html.parser'))
  link=soup.new_tag('link',rel='stylesheet',href='../notice.css');soup.head.append(link)
  (OUT/path).parent.mkdir(exist_ok=True,parents=True);(OUT/path).write_text(str(soup))
 for pid,items in by_pref.items():
  file=OUT/b.list_path(prefs[pid]['pref']);soup=BeautifulSoup(file.read_text(),'html.parser');nav='<section><h2>市町村の特典・助成・移動手段</h2><ul>'+''.join(f'<li><a href="{path}">{b.e(r["city"])}</a></li>' for r,path in items)+'</ul></section>';soup.main.insert(0,BeautifulSoup(nav,'html.parser'));file.write_text(str(soup))
 from public_home import render_home
 render_home(prefs,OUT,draft=draft)
 shutil.copy(ROOT/'assets/notice.css',OUT/'notice.css')
 (OUT/'notice.css').write_text((OUT/'notice.css').read_text()+'.local-menu{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}.local-menu a{padding:12px;border-bottom:1px solid #607080}.city-section{margin:36px 0;border-top:1px solid #52616d;padding-top:24px}section[id]{scroll-margin-top:20px}')
 if not draft:
  import xml.etree.ElementTree as ET
  ns='http://www.sitemaps.org/schemas/sitemap/0.9'
  ET.register_namespace('',ns)
  tree=ET.parse(OUT/'sitemap.xml');urlset=tree.getroot()
  existing={el.text for el in urlset.findall('{'+ns+'}url/{'+ns+'}loc')}
  for path in paths.values():
   if b.SITE+path not in existing:
    node=ET.SubElement(urlset,'{'+ns+'}url');ET.SubElement(node,'{'+ns+'}loc').text=b.SITE+path
  tree.write(OUT/'sitemap.xml',encoding='utf-8',xml_declaration=True)
 (OUT/'enriched-pages.json').write_text(json.dumps(paths,ensure_ascii=False,indent=2));print('built enriched pages',len(paths),'audit records',len(evidence))
if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--out',default=str(ROOT/'preview'));ap.add_argument('--publish',action='store_true');args=ap.parse_args()
 render(args.out,draft=not args.publish)
