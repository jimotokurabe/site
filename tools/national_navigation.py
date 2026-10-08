from pathlib import Path
from bs4 import BeautifulSoup
import json,html,shutil,hashlib
import argparse
ap=argparse.ArgumentParser()
ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
ap.add_argument('--out',type=Path,default=Path(__file__).resolve().parent)
args=ap.parse_args()
ROOT=args.root.resolve()
OUT=args.out.resolve()
OUT.mkdir(parents=True,exist_ok=True)

e=lambda s:html.escape(str(s),quote=True)
PREVIEW=set()
from build import REGIONS
from support_labels import support_labels
from warm_components import family_hero, family_strip, family_dialog
bus_data = {p.stem.removesuffix("-bus"): {c["slug"]: c for c in json.loads(p.read_text())["cities"]} for p in (ROOT/"data").glob("*-bus.json")}
taxi_data = {p.stem.removesuffix("-taxi"): json.loads(p.read_text())["cities"] for p in (ROOT/"data").glob("*-taxi.json")}
prefs={p.stem.replace('-menkyo-henno',''):json.loads(p.read_text()) for p in sorted((ROOT/'data').glob('*-menkyo-henno.json'))}
display_regions=[
 ('北海道',REGIONS[0][1][:1]),('東北',REGIONS[0][1][1:]),
 ('関東',REGIONS[1][1]),('中部',REGIONS[2][1]+REGIONS[3][1][:3]),
 ('近畿',[REGIONS[3][1][3]]+REGIONS[4][1]),('中国',REGIONS[5][1][:5]),
 ('四国',REGIONS[5][1][5:]),('九州・沖縄',REGIONS[6][1]),
]
regions=[(name,[(pid,prefs[pid]['pref']['name']) for pid in ids if pid in prefs and not prefs[pid]['pref'].get('draft')]) for name,ids in display_regions]
PREVIEW={p+':'+c['slug'] for p,d in prefs.items() for c in d['cities']}
records=[]
for p,d in prefs.items():
 for c in d['cities']:
  path=f"{p}-menkyo-henno/{c['slug']}.html"
  records.append(dict(name=c['n'],kana=c.get('y',''),pref=d['pref']['name'],pid=p,region=c.get('r',''),url=path if p+':'+c['slug'] in PREVIEW else 'https://jimotokurabe.jp/'+path,preview=p+':'+c['slug'] in PREVIEW, labels=support_labels(c, bus_data.get(p,{}).get(c['slug']), taxi_data.get(p,{}).get(c['slug']))))

SIZEJS="""function applySize(size){const big=size==='large';document.documentElement.classList.toggle('large',big);document.querySelectorAll('[data-size]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.size===(big?'large':'normal'))));}try{applySize(sessionStorage.getItem('jk-national-size')||'normal');}catch(e){}document.querySelectorAll('[data-size]').forEach(b=>b.addEventListener('click',()=>{applySize(b.dataset.size);try{sessionStorage.setItem('jk-national-size',b.dataset.size);}catch(e){}}));"""

def shell(title,body,script='',description=''):
 return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>{e(title)}｜じもとくらべ</title><meta name="description" content="{e(description)}"><link rel="stylesheet" href="assets/warm-shared.css"><link rel="stylesheet" href="assets/warm-navigation.css"></head><body><a href="#main" class="skip">本文へ移動</a><div class="draft">全国版・未公開プレビュー ／ 制度の内容は既存の掲載記録を使用</div><div class="wrap"><header class="mast"><a class="brand" href="index.html">じもと<span>くらべ</span></a><div class="size" role="group" aria-label="文字の大きさ"><span>文字の大きさ</span><button data-size="normal" aria-pressed="true" type="button">標準</button><button data-size="large" aria-pressed="false" type="button">大きく</button></div></header><main id="main">{body}</main><footer><p>制度ごとに対象条件・出典・確認日を確認し、申請前に公式窓口の最新の案内をお確かめください。</p><p>掲載範囲は市町村によって異なります。掲載がないことは、制度がないことを意味しません。</p><a href="index.html">トップへ</a></footer></div>{family_dialog()}<script>{SIZEJS}{script}</script><script src="assets/warm-experience.js" defer></script></body></html>'''
LABEL_HELP = 'ラベルは掲載情報に基づく目印です。対象年齢・申請期限などは詳細で確認してください。「要確認」は現行性などの確認が必要な情報です。ラベルがないことは制度がないことを意味しません。県共通の割引だけの場合は「返納特典あり」に含めません。'

assets=OUT/'assets'
assets.mkdir(parents=True,exist_ok=True)
if (ROOT/'assets/warm-navigation.css').resolve() != (assets/'warm-navigation.css').resolve():
    shutil.copy2(ROOT/'assets/warm-navigation.css',assets/'warm-navigation.css')

def labels_html(labels):
 return '<span class="support-labels">'+''.join('<span class="support-label support-label--'+e(item['kind'])+(' support-label--uncertain' if item['uncertain'] else '')+'">'+e(item['text'])+'</span>' for item in labels)+'</span>' if labels else ''
def citylink(c):
 mark='支援をまとめて見る →' if c['preview'] else '現在の公開ページ ↗'
 return f'<a class="{"preview" if c["preview"] else ""}" href="{e(c["url"])}"><span class="city-label-main"><strong>{e(c["name"])}</strong><small>{e(c["kana"])}</small>{labels_html(c["labels"])}</span><small class="resultmark">{mark}</small></a>'
commonjs="""const normalize=s=>s.normalize('NFKC').toLowerCase().replace(/[ァ-ヶ]/g,c=>String.fromCharCode(c.charCodeAt(0)-96)).replace(/[\\s　]/g,'');const matches=(c,q)=>[c.name,c.kana,c.pref+c.name,c.pref+c.kana].some(v=>normalize(v).includes(q));"""
regionhtml='<div class="region-buttons" role="group" aria-label="地方を選ぶ">'+''.join(
 f'<button type="button" class="region-toggle" data-region-toggle="{i}" aria-expanded="{str(i==4).lower()}" aria-controls="region-panel-{i}"><span>{e(n)}</span><span class="region-indicator" aria-hidden="true">{"−" if i==4 else "＋"}</span></button>'
 for i,(n,ps) in enumerate(regions))+'</div><div class="region-panels">'+''.join(
 f'<section class="region-panel" id="region-panel-{i}" aria-label="{e(n)}の都道府県"'+('' if i==4 else ' hidden')+'><ul class="prefgrid">'+''.join(f'<li><a class="tile" href="{p}-menkyo-henno.html">{e(name)}<span aria-hidden="true">›</span></a></li>' for p,name in ps)+'</ul></section>'
 for i,(n,ps) in enumerate(regions))+'</div>'
body='''<section class="hero"><div class="intro"><p class="eyebrow">ご本人も、離れて暮らすご家族も</p><h1>免許を返したあとの<br>移動と支援を探す。</h1><p class="lead">バス代やタクシー代の支援、通院・買い物の足を、お住まいの市町村から確認できます。</p><p class="reassure">まだ返納していなくても大丈夫。<br>返納を条件にしない支援も案内します。</p></div><section class="finder" id="search" aria-labelledby="search-title"><h2 id="search-title">お住まいの市町村は？</h2><form id="search-form" role="search"><label for="city-query">市・区・町・村の名前</label><div class="inputline"><input id="city-query" type="search" placeholder="例：こうべ、神戸市" autocomplete="off" aria-describedby="search-help search-count" enterkeyhint="search"><button class="primary" type="submit">探す</button></div></form><p id="search-help" class="help">漢字・ひらがな・カタカナで探せます。</p><div class="examples"><span>入力例：</span><button type="button" data-example="神戸市">神戸市</button><button type="button" data-example="横浜市">横浜市</button><button type="button" data-example="鹿児島市">鹿児島市</button></div><p class="search-status" id="search-count" role="status" aria-live="polite">名前の一部でも候補が表示されます。</p><ul class="results" id="city-results" aria-label="市町村の検索結果" hidden></ul><button id="more" class="more" hidden type="button">続きを表示</button><a class="alternative" href="#prefectures">都道府県の一覧から選ぶ ↓</a></section></section><div class="guide-strip" aria-label="このサイトの使い方"><div><span>1</span>住んでいる市町村を選ぶ</div><div><span>2</span>対象条件と費用を確認</div><div><span>3</span>申請先・公式の案内へ</div></div><section class="section" id="prefectures"><div class="section-head"><h2>都道府県から探す</h2><p>都道府県 → 市町村の順に選べます。</p></div><nav class="region-jump" aria-label="地方へ移動">'''+''.join(f'<a href="#region-{i}">{e(n)} ↓</a>' for i,(n,_) in enumerate(regions))+'''</nav>'''+regionhtml+'''</section><section class="section"><h2>市町村のページで確認できること</h2><p class="muted">制度名が分からなくても、市町村を選べばまとめて探せます。</p><div class="four"><article><p class="tag">免許を返した方へ</p><h3>免許返納の特典</h3><p>返納した方の割引・支援。年齢や申請期限も確認します。</p></article><article><p class="tag">ふだんの外出に</p><h3>バス助成・敬老パス</h3><p>対象年齢、自己負担、使える路線を確認します。</p></article><article><p class="tag">タクシーを使うとき</p><h3>タクシー助成</h3><p>利用券・割引の対象条件と、申請先を確認します。</p></article><article><p class="tag">通院・買い物に</p><h3>地域の移動手段</h3><p>コミュニティバスや乗合交通。掲載範囲も確認します。</p></article></div></section><section class="section"><h2>返納を決める前にも、ご家族と。</h2><p>支援があっても、いつもの病院やお店まで行けるとは限りません。行き先・帰りの便・費用も合わせて確認しましょう。</p><div class="guide-links"><a href="https://jimotokurabe.jp/menkyo-henno-guide.html">返納の手続き・基本を読む ↗</a><a href="https://jimotokurabe.jp/henno-hanashikata.html">親に運転の話をするときのヒント ↗</a></div><p class="help">この2つのリンクは、現在の公開ページを開きます。</p></section>'''
js='const cities='+json.dumps(records,ensure_ascii=False).replace('</','<\\/')+';'+commonjs+'''
const input=document.getElementById('city-query'),results=document.getElementById('city-results'),status=document.getElementById('search-count'),more=document.getElementById('more');let limit=8;let composing=false;
function render(){const q=normalize(input.value);results.replaceChildren();more.hidden=true;results.hidden=!q;if(!q){status.textContent='名前の一部でも候補が表示されます。';return;}const found=cities.filter(c=>matches(c,q)).sort((a,b)=>Number(normalize(b.name)===q||normalize(b.kana)===q)-Number(normalize(a.name)===q||normalize(a.kana)===q));status.textContent=found.length?found.length+'件見つかりました。都道府県名も確認して選んでください。':'見つかりませんでした。市町村名を短くするか、下の都道府県一覧からお探しください。';for(const c of found.slice(0,limit)){const li=document.createElement('li'),a=document.createElement('a'),text=document.createElement('span'),strong=document.createElement('strong'),sub=document.createElement('small'),mark=document.createElement('span');a.href=c.url;strong.textContent=c.name;sub.textContent=c.pref+' ／ '+c.kana;mark.className='resultmark';mark.textContent=c.preview?'支援をまとめて見る →':'現在の公開ページ ↗';text.className='city-label-main';text.append(strong,sub);if(c.labels.length){const badges=document.createElement('span');badges.className='support-labels';for(const item of c.labels){const badge=document.createElement('span');badge.className='support-label support-label--'+item.kind+(item.uncertain?' support-label--uncertain':'');badge.textContent=item.text;badges.append(badge);}text.append(badges);}a.append(text,mark);li.append(a);results.append(li);}more.hidden=found.length<=limit;more.textContent='次の'+Math.min(8,found.length-limit)+'件を表示（'+Math.min(limit,found.length)+' / '+found.length+'件）';}
input.addEventListener('compositionstart',()=>composing=true);input.addEventListener('compositionend',()=>{composing=false;limit=8;render();});input.addEventListener('input',()=>{if(!composing){limit=8;render();}});document.getElementById('search-form').addEventListener('submit',ev=>{ev.preventDefault();if(composing)return;limit=8;render();const first=results.querySelector('a');if(first)first.focus();else input.focus();});document.querySelectorAll('[data-example]').forEach(b=>b.addEventListener('click',()=>{input.value=b.dataset.example;limit=8;render();input.focus();}));more.addEventListener('click',()=>{const n=limit;limit+=8;render();results.querySelectorAll('a')[n]?.focus();});
'''
home=BeautifulSoup(body,'html.parser')
hero=home.select_one('.hero')
hero.select_one('.eyebrow').string='いつものまちで、これからも。'
hero.h1.clear();hero.h1.append(BeautifulSoup('免許返納の特典を、<br>お住まいの地域から。','html.parser'))
hero.select_one('.lead').string='バス代やタクシー代の支援、通院・買い物の足を、市町村ごとに確認できます。'
hero.append(BeautifulSoup(family_hero(),'html.parser'))
hero['class']=['hero','warm-home-hero']
finder=hero.select_one('.finder').extract()
search=BeautifulSoup('<details class="secondary-search" id="search"><summary>市町村名を入力して探す <span aria-hidden="true">⌄</span></summary></details>','html.parser').details
finder.attrs.pop('id',None)
search.append(finder)
directory=home.select_one('#prefectures')
directory['class']=['directory'];directory['id']='prefectures'
directory.select_one('h2').string='お住まいの地域を選ぶ'
directory.select_one('.region-jump').decompose()
directory.append(search)
home.select_one('.guide-strip').decompose()
label_note=home.new_tag('p',attrs={'class':'label-help','id':'label-help'});label_note.string=LABEL_HELP
home.select_one('#city-results').insert_after(label_note)
home.select_one('#city-results')['aria-describedby']='label-help'
home.select_one('#search-title').string='全国の市区町村から探す'
for link in home.select('.guide-links a'):
    link['href']=link['href'].replace('https://jimotokurabe.jp/','')
for note in home.select('.guide-links + .help'):note.decompose()
home.select_one('.section:last-of-type').insert_before(BeautifulSoup(family_strip(),'html.parser'))
js+='''
const regionButtons=[...document.querySelectorAll('[data-region-toggle]')];
regionButtons.forEach(button=>button.addEventListener('click',()=>{const open=button.getAttribute('aria-expanded')!=='true';for(const other of regionButtons){const active=open&&other===button;other.setAttribute('aria-expanded',String(active));other.querySelector('.region-indicator').textContent=active?'−':'＋';document.getElementById(other.getAttribute('aria-controls')).hidden=!active;}}));
function openHashSearch(){if(location.hash==='#search'||location.hash==='#city-query'){document.getElementById('search').open=true;if(location.hash==='#city-query')requestAnimationFrame(()=>document.getElementById('city-query').scrollIntoView());}}
window.addEventListener('hashchange',openHashSearch);openHashSearch();
'''
(OUT/'index.html').write_text(shell('免許返納特典・高齢者の移動支援を市町村から探す',str(home),js,'免許返納の特典、バス助成・敬老パス、タクシー支援、通院・買い物の交通を市町村から探せます。返納の要否、対象条件、費用、申請先を確認できます。掲載範囲は地域により異なります。'))
for p,d in prefs.items():
 name=d['pref']['name'];cs=[c for c in records if c['pid']==p];groups=d['regions']
 regionoptions=''.join(f'<option value="{e(r["id"])}">{e(r["name"])}</option>' for r in groups)
 listing=''
 for r in groups:
  rc=[c for c in cs if c['region']==r['id']]
  listing+=f'<section class="city-group" data-region="{e(r["id"])}"><h3>{e(r["name"])}</h3><ul class="citylist">'+''.join(f'<li data-name="{e(c["name"])}" data-kana="{e(c["kana"])}">{citylink(c)}</li>' for c in rc)+'</ul></section>'
 body=f'''<nav class="crumbs" aria-label="いまいる場所"><a href="index.html">トップ</a> ＞ {e(name)}</nav><header class="pref-intro"><p class="eyebrow">{e(name)}の移動と支援</p><h1>お住まいの市町村を選んでください</h1><p>免許返納の特典、バス・タクシーの支援、地域の移動手段は、市町村のページで確認できます。</p></header><p class="sample-note">市町村を選ぶと、支援の対象条件・費用・申請先を確認できます。</p><p class="label-help" id="label-help">{e(LABEL_HELP)}</p><div class="pref-layout"><section class="finder" aria-labelledby="filter-title"><h2 id="filter-title">{e(name)}内を探す</h2><form id="filter-form" role="search"><label for="city-query">市町村名で絞り込む</label><div class="inputline"><input id="city-query" type="search" placeholder="例：名前・よみがな" autocomplete="off" enterkeyhint="search"><button class="primary" type="submit">探す</button></div><label class="filter-label" for="area">地域から絞り込む</label><select id="area"><option value="">すべての地域</option>{regionoptions}</select><button id="reset" class="reset" type="button">絞り込みを解除</button></form><p class="help">返納の有無や年齢は、詳細ページで確認できます。</p><a class="alternative" href="index.html#prefectures">別の都道府県を選ぶ</a></section><section aria-label="市町村の一覧" aria-describedby="label-help"><p class="count" id="count" role="status" aria-live="polite">{len(cs)}市区町村を表示しています。</p><div id="empty" class="empty" hidden><p>一致する市町村が見つかりませんでした。</p><p>名前を短くするか、地域の絞り込みを解除してください。</p><button type="button" id="empty-reset">すべての市町村を表示</button></div>{listing}</section></div><section class="section"><h2>選んだ先では、条件から確認できます</h2><p>「返納した方の特典」と「返納を条件にしない支援」を分けて読み、対象年齢・費用・申請先を確認します。制度が終了している場合や、確認が必要な点も記載します。</p></section>'''
 body+=family_strip()
 js=commonjs+'''
const input=document.getElementById('city-query'),area=document.getElementById('area');let composing=false;
function filter(){const q=normalize(input.value);let n=0;document.querySelectorAll('.city-group').forEach(group=>{let gn=0;group.querySelectorAll('li').forEach(li=>{const ok=(!area.value||group.dataset.region===area.value)&&[li.dataset.name,li.dataset.kana].some(v=>normalize(v).includes(q));li.hidden=!ok;if(ok)gn++;});group.hidden=!gn;n+=gn;});document.getElementById('count').textContent=n+'市区町村を表示しています。';document.getElementById('empty').hidden=n!==0;}
input.addEventListener('compositionstart',()=>composing=true);input.addEventListener('compositionend',()=>{composing=false;filter();});input.addEventListener('input',()=>{if(!composing)filter();});area.addEventListener('change',filter);document.getElementById('filter-form').addEventListener('submit',ev=>{ev.preventDefault();filter();document.querySelector('.city-group:not([hidden]) li:not([hidden]) a')?.focus();});function reset(){input.value='';area.value='';filter();input.focus();}document.getElementById('reset').addEventListener('click',reset);document.getElementById('empty-reset').addEventListener('click',reset);
'''
 (OUT/f'{p}-menkyo-henno.html').write_text(shell(name+'の免許返納特典・高齢者の移動支援｜市町村一覧',body,js,name+'の'+str(len(cs))+'市区町村から、免許返納特典やバス・タクシー支援の案内を探せます。市町村の詳細ページで対象条件・費用・申請先・確認日を確認できます。掲載がないことは制度がないことを意味しません。'))
print('Built nationwide navigation:',len(prefs),'prefectures,',len(records),'municipalities')
