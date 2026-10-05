"""兵庫県の地域案内図と特徴付き市町一覧を生成する。"""
import json, shutil
import build as b
from bs4 import BeautifulSoup

def render_hyogo(out, draft=False):
 OUT=out
 d=b.load_pref(b.ROOT/'data/hyogo-menkyo-henno.json')
 regions=d['regions'];cities=d['cities']
 mobility={}
 for f in ['east-harima-mobility.json','municipal-mobility.json']:
  for m in json.loads((b.ROOT/'data'/f).read_text())['cities']:
   if f=='municipal-mobility.json' and m.get('pref')!='hyogo':continue
   key=m.get('municipality',m['id'])
   if key=='kobe-nishi':key='kobe'
   if m.get('rides'):mobility[key]=m['rides'][0]
 # 簡略図。測量上の境界ではなく、地域の位置関係を示す。
 shapes={
  'tajima':('M106 42 L210 25 L264 50 L284 111 L258 181 L190 188 L150 214 L107 185 L81 122 Z',184,107),
  'tamba':('M288 91 L345 84 L394 113 L415 179 L379 230 L323 220 L292 179 L273 177 L298 118 Z',350,154),
  'nishi-harima':('M65 164 L94 196 L143 225 L152 285 L127 341 L52 322 L30 264 L40 202 Z',88,263),
  'naka-harima':('M153 222 L191 199 L250 194 L246 245 L215 289 L173 312 L137 340 L162 282 Z',195,253),
  'kita-harima':('M260 192 L284 190 L314 232 L348 237 L334 280 L289 309 L236 289 L257 247 Z',285,247),
  'higashi-harima':('M229 299 L284 320 L313 351 L285 374 L215 349 L178 333 Z',245,332),
  'kobe-hanshin':('M355 245 L388 240 L423 214 L452 256 L429 319 L384 345 L326 365 L300 316 L339 291 Z',379,295),
  'awaji':('M270 400 L285 398 L297 424 L286 462 L264 490 L237 480 L247 449 Z',263,443),
 }
 map_svg='<svg class="region-map" viewBox="0 0 480 525" role="group" aria-label="兵庫県の地域案内図">'
 map_svg+='<text class="sea-label" x="32" y="38">日本海</text><text class="sea-label" x="54" y="429">瀬戸内海</text>'
 for r in regions:
  path,x,y=shapes[r['id']];count=sum(c['r']==r['id'] for c in cities)
  active=r['id']=='higashi-harima'
  map_svg+=f'<g id="r-{r["id"]}" role="button" tabindex="0" data-region="{r["id"]}" aria-label="{r["name"]}、{count}市町を表示" aria-pressed="{str(active).lower()}" class="map-region{ " selected" if active else ""}"><path d="{path}"/><text x="{x}" y="{y}" class="map-name">{r["name"]}</text><text x="{x}" y="{y+21}" class="map-count">{count}市町</text></g>'
 map_svg+='</svg>'
 main='''<nav class="crumbs" aria-label="いまいる場所"><a href="./">トップ</a><span> ＞ </span>兵庫県</nav>
 <header class="pref-intro"><p class="pref-kicker">兵庫県の暮らしと移動</p><h1>あなたの町では、<br>どんな支援が使える？</h1><p>免許返納の特典、交通費の助成、通院・買い物の移動手段。<br>お住まいの地域から、市町ごとの案内を探せます。</p></header>
 <div class="pref-explorer"><section class="map-panel" aria-labelledby="map-heading"><div class="panel-heading"><h2 id="map-heading">地域から選ぶ</h2><span>兵庫県 41市町</span></div>'''+map_svg+'''<p class="map-caption">地域の位置関係を簡略化した案内図です。<br>地域名を押すと、市町の一覧が切り替わります。</p><div class="region-switch" role="group" aria-label="地域を選択">'''
 for r in regions:
  main+=f'<button type="button" data-region="{r["id"]}" aria-pressed="{str(r["id"]=="higashi-harima").lower()}">{r["name"]}</button>'
 main+='''<button type="button" data-region="all" aria-pressed="false">県内すべて</button></div></section>
 <section class="city-panel" aria-labelledby="city-heading"><div class="search-line"><label for="pref-query">市町名で探す</label><input id="pref-query" type="search" placeholder="例：明石市、姫路市" autocomplete="off"></div><div class="city-title"><div><p id="region-caption">瀬戸内海沿いの地域</p><h2 id="city-heading">東播磨</h2></div><span id="city-count" role="status" aria-live="polite">5市町</span></div><p class="city-instruction">気になる市町を選び、対象条件や公式案内をご確認ください。</p><ul class="city-lines">'''
 for c in cities:
  # 既存掲載内容の冒頭文を利用。金額だけで制度を比較しない。
  summary=c['what'].split('。')[0]+'。'
  if c.get('k') in ['notfound','none','end'] and c['slug'] in mobility:
   ride=mobility[c['slug']];summary='移動案内：'+ride['name']+'。'+ride.get('summary','').split('。')[0]+'。'
  if len(summary)>95:summary=summary[:92]+'…'
  main+=f'<li id="{c["slug"]}" data-city="{b.e(c["n"])}" data-city-region="{c["r"]}"'+(' hidden' if c['r']!='higashi-harima' else '')+f'><a href="hyogo-menkyo-henno/{c["slug"]}.html"><div><h3>{b.e(c["n"])}</h3><p>{b.e(summary)}</p></div><span class="row-arrow" aria-hidden="true">→</span><span class="sr-only">の特典・助成・移動手段を見る</span></a></li>'
 main+='''</ul><p id="no-cities" hidden>該当する市町が見つかりません。名前を短くしてお試しください。</p><p class="list-note">ここでは掲載内容の一部をご紹介しています。対象年齢・期限・最新の確認状況は、個別ページでご確認ください。</p></section></div>
 <section class="pref-common" id="statewide"><p class="common-label">市町をまたいで使える支援</p><h2>県内共通の割引もあります。</h2><p>運転経歴証明書を提示して利用できる、兵庫県内の協賛企業・団体の特典。年齢や住所などの条件と、現在の特典を公式一覧で確認できます。</p><a href="https://www.police.pref.hyogo.lg.jp/traffic/license/keireki_tokuten/index.htm" target="_blank" rel="noopener">兵庫県警の特典一覧を見る ↗</a></section>'''
 script='''<script>(()=>{const regions=REGIONS,rows=[...document.querySelectorAll('[data-city]')],controls=[...document.querySelectorAll('[data-region]')],input=document.querySelector('#pref-query');let region='higashi-harima';const captions={'higashi-harima':'瀬戸内海沿いの地域','tajima':'県北部の地域','tamba':'県東部の地域','awaji':'淡路島の地域'};function update(){const q=input.value.trim();let count=0;for(const row of rows){const show=q?row.dataset.city.includes(q):(region==='all'||row.dataset.cityRegion===region);row.hidden=!show;if(show)count++;}for(const el of controls){const selected=!q&&el.dataset.region===region;el.setAttribute('aria-pressed',String(selected));el.classList.toggle('selected',selected);}document.querySelector('#city-heading').textContent=q?'「'+q+'」の検索結果':region==='all'?'兵庫県のすべての市町':regions[region];document.querySelector('#region-caption').textContent=q?'県内41市町から検索':region==='all'?'お住まいの市町を選んでください':captions[region]||'兵庫県の地域';document.querySelector('#city-count').textContent=count+'市町';document.querySelector('#no-cities').hidden=count!==0;}function choose(el){region=el.dataset.region;input.value='';update();}for(const el of controls){el.addEventListener('click',()=>choose(el));if(el.tagName.toLowerCase()==='g')el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(el);}});}input.addEventListener('input',update);function showHash(){const id=decodeURIComponent(location.hash.slice(1));const row=rows.find(r=>r.id===id);if(row){region=row.dataset.cityRegion;input.value='';update();row.scrollIntoView();}}window.addEventListener('hashchange',showHash);showHash();})();</script>'''.replace('REGIONS',json.dumps({r['id']:r['name'] for r in regions},ensure_ascii=False))
 s=BeautifulSoup(b.shell(title='兵庫県｜市町ごとの特典・助成・移動手段｜じもとくらべ',description='兵庫県の地域から、お住まいの市町の免許返納特典・交通費助成・移動手段を探せます。',path='hyogo-menkyo-henno.html',main=main,draft=draft,scripts=script),'html.parser')
 if draft:
  for el in s.select('script'):
   if 'gtag' in str(el) or 'googletagmanager' in el.get('src',''):el.decompose()
 for el in s.select('.draft'):el.decompose()
 s.body['class']=['pref-regional'];s.head.append(s.new_tag('link',rel='stylesheet',href='hyogo-region.css'))
 nav=s.select_one('.site-nav');nav.clear();nav.append(BeautifulSoup('<a href="./">地域を探す</a><a href="https://jimotokurabe.jp/menkyo-henno-guide.html">免許返納の基本</a>','html.parser'))
 (OUT/'hyogo-menkyo-henno.html').write_text(str(s))
 shutil.copy(b.ROOT/"assets/hyogo-region.css",OUT/"hyogo-region.css")
