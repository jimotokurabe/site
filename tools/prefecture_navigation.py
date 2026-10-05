"""県別設定から地域案内図と特徴付き市町村一覧を生成する。"""
import json, shutil
import build as b
from bs4 import BeautifulSoup

def render_prefecture(pid, out, draft=False):
 OUT=out
 cfg=json.loads((b.ROOT/'data/prefecture-navigation.json').read_text())[pid]
 d=b.load_pref(b.ROOT/'data'/f'{pid}-menkyo-henno.json')
 pref=d['pref'];name=pref['name'];unit=pref['unit'];default=cfg['default_region']
 scope='都内' if pid=='tokyo' else '道内' if pid=='hokkaido' else '府内' if pid in {'osaka','kyoto'} else '県内'
 overrides=cfg.get('summaries',{})
 regions=d['regions'];cities=d['cities']
 mobility={}
 for f in ['east-harima-mobility.json','municipal-mobility.json']:
  if f=='east-harima-mobility.json' and pid!='hyogo':continue
  for m in json.loads((b.ROOT/'data'/f).read_text())['cities']:
   if f=='municipal-mobility.json' and m.get('pref')!=pid:continue
   key=m.get('municipality',m['id'])
   if key=='kobe-nishi':key='kobe'
   if m.get('rides'):mobility[key]=m['rides'][0]
 # 簡略図。測量上の境界ではなく、地域の位置関係を示す。
 shapes=cfg['shapes']
 assert set(shapes)=={r['id'] for r in regions},'案内図と地域区分が一致しません'
 assert all(c['r'] in shapes for c in cities),'所属地域が未設定です'
 region_name=next(r['name'] for r in regions if r['id']==default)
 default_count=sum(c['r']==default for c in cities)
 map_svg=f'<svg class="region-map" viewBox="{b.e(cfg.get("viewBox","0 0 480 525"))}" role="group" aria-label="{b.e(name)}の地域案内図">'
 for label in cfg.get('sea_labels',[]):
  map_svg+=f'<text class="sea-label" x="{label["x"]}" y="{label["y"]}">{b.e(label["text"])}</text>'
 for r in regions:
  path,x,y=shapes[r['id']];count=sum(c['r']==r['id'] for c in cities)
  active=r['id']==default
  label=b.e(cfg.get('map_labels',{}).get(r['id'],r['name']))
  map_svg+=f'<g id="r-{r["id"]}" role="button" tabindex="0" data-region="{r["id"]}" aria-label="{r["name"]}、{count}{unit}を表示" aria-pressed="{str(active).lower()}" class="map-region{ " selected" if active else ""}"><path d="{b.e(path)}"/><text x="{x}" y="{y}" class="map-name">{label}</text><text x="{x}" y="{y+21}" class="map-count">{count}{unit}</text></g>'
 map_svg+='</svg>'
 main=f'''<nav class="crumbs" aria-label="いまいる場所"><a href="./">トップ</a><span> ＞ </span>{b.e(name)}</nav>
 <header class="pref-intro"><p class="pref-kicker">{b.e(name)}の暮らしと移動</p><h1>あなたの町では、<br>どんな支援が使える？</h1><p>免許返納の特典、交通費の助成、通院・買い物の移動手段。<br>お住まいの地域から、市町村ごとの案内を探せます。</p></header>
 <div class="pref-explorer"><section class="map-panel" aria-labelledby="map-heading"><div class="panel-heading"><h2 id="map-heading">地域から選ぶ</h2><span>{b.e(name)} {len(cities)}{unit}</span></div>'''+map_svg+'''<p class="map-caption">地域の位置関係を簡略化した案内図です。<br>地域名を押すと、市町村の一覧が切り替わります。</p><div class="region-switch" role="group" aria-label="地域を選択">'''
 for r in regions:
  main+=f'<button type="button" data-region="{r["id"]}" aria-pressed="{str(r["id"]==default).lower()}">{r["name"]}</button>'
 main+=f'''<button type="button" data-region="all" aria-pressed="false">{scope}すべて</button></div></section>
 <section class="city-panel" aria-labelledby="city-heading"><div class="search-line"><label for="pref-query">市町村名で探す</label><input id="pref-query" type="search" placeholder="{b.e(cfg["placeholder"])}" autocomplete="off"></div><div class="city-title"><div><p id="region-caption">{b.e(cfg.get("captions",{}).get(default,name+"の地域"))}</p><h2 id="city-heading">{b.e(region_name)}</h2></div><span id="city-count" role="status" aria-live="polite">{default_count}{unit}</span></div><p class="city-instruction">気になる市町村を選び、対象条件や公式案内をご確認ください。</p><ul class="city-lines">'''
 for c in cities:
  # 既存掲載内容の冒頭文を利用。金額だけで制度を比較しない。
  summary=c['what'].split('。')[0]+'。'
  if c.get('k') in ['notfound','none','end'] and c['slug'] in mobility:
   ride=mobility[c['slug']];summary='移動案内：'+ride['name']+'。'+ride.get('summary','').split('。')[0]+'。'
  summary=overrides.get(c['slug'],summary)
  if len(summary)>95:summary=summary[:92]+'…'
  main+=f'<li id="{c["slug"]}" data-city="{b.e(c["n"])}" data-city-region="{c["r"]}"'+(' hidden' if c['r']!=default else '')+f'><a href="{b.guide_dir(pref)}/{c["slug"]}.html"><div><h3>{b.e(c["n"])}</h3><p>{b.e(summary)}</p></div><span class="row-arrow" aria-hidden="true">→</span><span class="sr-only">の特典・助成・移動手段を見る</span></a></li>'
 main+=f'''</ul><noscript><style>.city-lines li[hidden]{{display:list-item}}</style><p>すべての市町村を表示しています。</p></noscript><p id="no-cities" hidden>該当する市町村が見つかりません。名前を短くしてお試しください。</p><p class="list-note">ここでは掲載内容の一部をご紹介しています。対象年齢・期限・最新の確認状況は、個別ページでご確認ください。</p></section></div>
'''
 if pref.get('statewide'):
  main+=f'''<section class="pref-common" id="statewide"><p class="common-label">市町村をまたいで使える支援</p><h2>{b.e(pref['statewide']['title'])}</h2><p>{b.e(cfg.get('common_intro',pref['statewide']['body'][0]))}</p><a href="{b.e(pref['statewide']['link_url'])}" target="_blank" rel="noopener">{b.e(pref['statewide']['link_label'])} ↗</a></section>'''
 script='''<script>(()=>{const regions=REGIONS,rows=[...document.querySelectorAll('[data-city]')],controls=[...document.querySelectorAll('[data-region]')],input=document.querySelector('#pref-query');let region=DEFAULT;const captions=CAPTIONS,prefName=PREFNAME,unit=UNIT,total=TOTAL,scope=SCOPE;function update(){const q=input.value.trim();let count=0;for(const row of rows){const show=q?row.dataset.city.includes(q):(region==='all'||row.dataset.cityRegion===region);row.hidden=!show;if(show)count++;}for(const el of controls){const selected=!q&&el.dataset.region===region;el.setAttribute('aria-pressed',String(selected));el.classList.toggle('selected',selected);}document.querySelector('#city-heading').textContent=q?'「'+q+'」の検索結果':region==='all'?prefName+'のすべての市町村':regions[region];document.querySelector('#region-caption').textContent=q?scope+total+unit+'から検索':region==='all'?'お住まいの市町村を選んでください':captions[region]||prefName+'の地域';document.querySelector('#city-count').textContent=count+unit;document.querySelector('#no-cities').hidden=count!==0;}function choose(el){region=el.dataset.region;input.value='';update();}for(const el of controls){el.addEventListener('click',()=>choose(el));if(el.tagName.toLowerCase()==='g')el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(el);}});}input.addEventListener('input',update);function showHash(){const id=location.hash.slice(1);const row=rows.find(r=>r.id===id);if(row){region=row.dataset.cityRegion;input.value='';update();row.scrollIntoView();}}window.addEventListener('hashchange',showHash);showHash();})();</script>'''.replace('REGIONS',json.dumps({r['id']:r['name'] for r in regions},ensure_ascii=False)).replace('DEFAULT',json.dumps(default)).replace('CAPTIONS',json.dumps(cfg.get('captions',{}),ensure_ascii=False)).replace('PREFNAME',json.dumps(name,ensure_ascii=False)).replace('UNIT',json.dumps(unit,ensure_ascii=False)).replace('TOTAL',str(len(cities))).replace('SCOPE',json.dumps(scope,ensure_ascii=False))
 s=BeautifulSoup(b.shell(title=name+'｜市町村ごとの特典・助成・移動手段｜じもとくらべ',description=name+'の地域から、お住まいの市町村の免許返納特典・交通費助成・移動手段を探せます。',path=b.list_path(pref),main=main,draft=draft,scripts=script),'html.parser')
 if draft:
  for el in s.select('script'):
   if 'gtag' in str(el) or 'googletagmanager' in el.get('src',''):el.decompose()
 for el in s.select('.draft'):el.decompose()
 s.body['class']=['pref-regional'];s.head.append(s.new_tag('link',rel='stylesheet',href='prefecture-region.css'))
 nav=s.select_one('.site-nav');nav.clear();nav.append(BeautifulSoup('<a href="./">地域を探す</a><a href="https://jimotokurabe.jp/menkyo-henno-guide.html">免許返納の基本</a>','html.parser'))
 (OUT/b.list_path(pref)).write_text(str(s))
 shutil.copy(b.ROOT/"assets/prefecture-region.css",OUT/"prefecture-region.css")
