"""Visitor-facing regional entry page; indexing remains disabled in local previews."""
import json
from bs4 import BeautifulSoup
import build as b

def render_home(prefs, out, draft=True):
 regions=[('北海道・東北','hokkaido aomori iwate miyagi akita yamagata fukushima'),('関東','ibaraki tochigi gunma saitama chiba tokyo kanagawa'),('中部','niigata toyama ishikawa fukui yamanashi nagano gifu shizuoka aichi'),('近畿','mie shiga kyoto osaka hyogo nara wakayama'),('中国・四国','tottori shimane okayama hiroshima yamaguchi tokushima kagawa ehime kochi'),('九州・沖縄','fukuoka saga nagasaki kumamoto oita miyazaki kagoshima okinawa')]
 main='''<section class="home-intro"><p class="home-kicker">じもとの制度を、じもとの暮らしに。</p><h1>免許を返したあとの<br>移動と支援を探す。</h1><p class="home-lead">免許返納の特典、タクシー助成、通院や買い物の移動手段。<br>お住まいの市町村ごとに、利用条件と公式の案内を確認できます。</p><a class="home-jump" href="#search">お住まいの地域から探す <span aria-hidden="true">↓</span></a></section><section id="search" class="home-search"><h2>市町村名から探す</h2><label for="city-query">市・区・町・村の名前</label><input id="city-query" type="search" placeholder="例：明石市、ひたちなか市" autocomplete="off"><p id="search-count" role="status" aria-live="polite">市町村名を入力すると、候補が表示されます。</p><ul id="city-results" hidden></ul></section><section class="home-regions" aria-labelledby="pref-heading"><h2 id="pref-heading">都道府県から探す</h2><p>都道府県を選び、次の画面で市町村を選んでください。</p>'''
 for name,ids in regions:
  main+='<section class="region-line"><h3>'+name+'</h3><ul>'
  for pid in ids.split():
   d=prefs[pid];main+='<li><a href="'+b.e(b.list_path(d['pref']))+'">'+b.e(d['pref']['name'])+'<span aria-hidden="true">›</span></a></li>'
  main+='</ul></section>'
 main+='''</section><section id="return" class="home-about"><h2>利用する前に、条件を確認。</h2><p>同じ支援でも、年齢、住んでいる地域、申請期限などは市町村によって異なります。各ページの確認日と対象条件を読み、申請や利用の前に公式窓口で最新の案内をご確認ください。</p></section>'''
 bus_prefs=[d for d in prefs.values() if d.get('bus') and (draft or (not d['bus'].get('draft') and not d['pref'].get('draft')))]
 if bus_prefs:
  links=''.join(f'<li><a href="{b.bus_path(d["pref"])}">{b.e(d["pref"]["name"])}の高齢者バス助成・敬老パス{"（確認用下書き）" if d["bus"].get("draft") else ""}</a></li>' for d in sorted(bus_prefs,key=lambda d:d['pref']['id']))
  main+=f'<section id="bus" class="home-about" aria-labelledby="bus-heading"><h2 id="bus-heading">高齢者のバス支援を比べる</h2><ul>{links}</ul></section>'
 cities=[]
 for pid,d in prefs.items():
  for c in d['cities']:
   guide=b.guide_dir(d['pref'])+'/'+c['slug']+'.html'
   cities.append({'name':c['n'],'pref':d['pref']['name'],'url':guide if (out/guide).exists() else b.list_path(d['pref'])})
 script='''<script>(()=>{const cities=DATA;const input=document.getElementById('city-query'),list=document.getElementById('city-results'),count=document.getElementById('search-count');input.addEventListener('input',()=>{const q=input.value.trim();list.replaceChildren();list.hidden=!q;if(!q){count.textContent='市町村名を入力すると、候補が表示されます。';return;}const hits=cities.filter(c=>(c.pref+c.name).includes(q));count.textContent=hits.length?hits.length+'件の候補があります。':'候補が見つかりません。都道府県から探すこともできます。';for(const c of hits){const li=document.createElement('li'),a=document.createElement('a');a.href=c.url;a.textContent=c.name+'（'+c.pref+'）';li.append(a);list.append(li);}});})();</script>'''.replace('DATA',json.dumps(cities,ensure_ascii=False).replace('</','<\\/'))
 soup=BeautifulSoup(b.shell(title='じもとくらべ｜市町村ごとの免許返納特典・交通費助成・移動手段',description='免許返納の特典、タクシー助成、通院・買い物の移動手段を市町村ごとに確認。都道府県から、お住まいの地域の制度と公式案内を探せます。',path='',main=main,draft=draft),'html.parser')
 if draft:
  for s in soup.select('script'):
   if 'gtag' in str(s) or 'googletagmanager' in s.get('src',''):s.decompose()
 for el in soup.select('.draft'):el.decompose()
 nav=soup.select_one('.site-nav');nav.clear();nav.append(BeautifulSoup('<a href="#search">地域を探す</a><a href="#return">利用前の確認</a>','html.parser'))
 soup.body['class']=['public-home'];soup.head.append(soup.new_tag('link',rel='stylesheet',href='home.css'));soup.body.append(BeautifulSoup(script,'html.parser'))
 (out/'index.html').write_text(str(soup))
 (out/'home.css').write_text('''.public-home{--home-ink:#e9edf0;--home-soft:#b5c2cc;--home-accent:#8bc6d1;--home-rule:#425664}.home-intro{padding:64px 0 44px;max-width:850px}.home-kicker{color:var(--home-accent);letter-spacing:.08em;font-size:.9rem}.home-intro h1{font-family:"BIZ UDPGothic",sans-serif;font-size:clamp(2rem,5vw,3.6rem);line-height:1.5;letter-spacing:.02em;margin:20px 0}.home-lead{line-height:2;color:var(--home-soft)}.home-jump{display:inline-flex;gap:40px;padding:16px 0;text-decoration:none;border-bottom:2px solid var(--home-accent);font-weight:700;margin-top:12px}.home-search{padding:32px 0;border-top:1px solid var(--home-rule)}.home-search label{display:block;margin:18px 0 8px}.home-search input{display:block;width:100%;max-width:620px;box-sizing:border-box;background:#1d2932;color:var(--home-ink);border:1px solid #78929e;border-radius:0;padding:16px;font:inherit}.home-search #search-count{color:var(--home-soft);font-size:.9rem}.home-search ul{list-style:none;padding:0;max-height:380px;overflow:auto}.home-search li{border-bottom:1px solid var(--home-rule)}.home-search li a{display:block;padding:16px 0}.home-regions{margin:24px 0 48px}.region-line{display:grid;grid-template-columns:140px 1fr;gap:24px;padding:24px 0;border-top:1px solid var(--home-rule)}.region-line h3{font-size:1rem;margin:12px 0}.region-line ul{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px 20px;list-style:none;margin:0;padding:0}.region-line a{display:flex;justify-content:space-between;align-items:center;padding:12px 0;text-decoration:none}.region-line a span{color:var(--home-accent)}.region-line a:hover{text-decoration:underline}.home-about{border-top:1px solid var(--home-rule);padding:24px 0;max-width:800px}.home-about p{line-height:2;color:var(--home-soft)}.public-home a:focus-visible,.public-home input:focus-visible{outline:3px solid var(--home-accent);outline-offset:5px}@media(max-width:650px){.home-intro{padding:30px 0}.home-lead br{display:none}.region-line{display:block;padding:20px 0}.region-line h3{margin:0 0 12px}.region-line ul{grid-template-columns:repeat(2,minmax(0,1fr));gap:4px 24px}.home-intro h1{font-size:2rem}.home-jump{gap:20px}}''')
