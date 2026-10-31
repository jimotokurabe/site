/* Exercise every generated prefecture page without fetching external resources. */
const {JSDOM}=require('jsdom'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const files=fs.readdirSync(path.join(root,'data')).filter(file=>file.endsWith('-menkyo-henno.json')).sort();
const normalize=text=>text.normalize('NFKC').toLowerCase().replace(/[ァ-ヶ]/g,c=>String.fromCharCode(c.charCodeAt(0)-96)).replace(/\s/g,'');
(async()=>{
 let pages=0,records=0;
 for(const file of files){
  const pref=JSON.parse(fs.readFileSync(path.join(root,'data',file),'utf8')),pid=pref.pref.id,unit=pref.pref.unit||'市区町村';
  const bus=JSON.parse(fs.readFileSync(path.join(root,'data',pid+'-bus.json'),'utf8'));
  const counts={return:pref.cities.length,bus:bus.cities.reduce((sum,city)=>sum+Math.max(1,city.programs.length),0),taxi:pref.cities.length};
  const dom=new JSDOM(fs.readFileSync(path.join(root,pid+'-menkyo-henno.html'),'utf8'),{url:'https://jimotokurabe.jp/'+pid+'-menkyo-henno.html?q=PRIVATE_QUERY',runScripts:'outside-only',pretendToBeVisual:true});
  const w=dom.window,d=w.document;w.performance.getEntriesByType=()=>[];w.HTMLElement.prototype.scrollIntoView=()=>{};
  for(const script of [...d.scripts]){
   if(['application/json','application/ld+json'].includes(script.type))continue;
   if(script.src){const url=new URL(script.src);if(url.origin===w.location.origin)w.eval(fs.readFileSync(path.join(root,url.pathname),'utf8'));}
   else if(script.textContent.trim())w.eval(script.textContent);
  }
  await new Promise(resolve=>setTimeout(resolve,0));
  const visible=()=>[...d.querySelectorAll('[data-comparison-row]')].filter(row=>!row.hidden&&!row.closest('[data-comparison-kind]').hidden);
  const input=d.querySelector('#city-query'),area=d.querySelector('#area');
  const query=value=>{input.value=value;input.dispatchEvent(new w.Event('input'));};
  const kind=value=>{const control=d.querySelector('[name="comparison-kind"][value="'+value+'"]');control.checked=true;control.dispatchEvent(new w.Event('change'));};
  assert.ok(d.querySelector('h1').textContent.includes(pref.pref.name),pid+' own heading');
  assert.equal(d.querySelector('.pref-comparison').dataset.municipalUnit,unit,pid+' municipal unit');
  for(const value of ['return','bus','taxi']){kind(value);assert.equal(visible().length,counts[value],pid+' '+value);}
  kind('all');assert.equal(visible().length,counts.return+counts.bus+counts.taxi,pid+' all');
  const selected=pref.cities.slice(0,2);
  query(selected.map(city=>city.n).join('、'));
  const terms=selected.map(city=>normalize(city.n));
  const expected=pref.cities.filter(city=>terms.some(term=>[city.n,city.y||''].some(value=>normalize(value).includes(term))));
  assert.equal(new Set(visible().map(row=>row.dataset.city)).size,expected.length,pid+' multiple names');
  area.value=selected[0].r;area.dispatchEvent(new w.Event('change'));
  assert.ok(visible().every(row=>row.dataset.region===selected[0].r),pid+' area AND names');
  query('PRIVATE_NO_CITY');assert.equal(visible().length,0);assert.equal(d.querySelector('#comparison-empty').hidden,false);
  d.querySelector('#reset').click();assert.equal(visible().length,counts.return+counts.bus+counts.taxi,pid+' reset');
  for(const link of d.querySelectorAll('.comparison-detail'))assert.ok(link.getAttribute('href').startsWith(pid+'-menkyo-henno/'),pid+' destination');
  const ids=[...d.querySelectorAll('[id]')].map(element=>element.id);assert.equal(ids.length,new Set(ids).size,pid+' unique IDs');
  const link=d.querySelector('.comparison-detail');link.addEventListener('click',event=>event.preventDefault());link.click();
  const events=Array.from(w.dataLayer||[],args=>Array.from(args)).filter(args=>args[0]==='event');
  assert.equal(events.filter(args=>args[1]==='related_support_click').length,1,pid+' existing tracking');
  assert.ok(!JSON.stringify(events).includes('PRIVATE_'),pid+' no query/input telemetry');
  pages++;records+=counts.return+counts.bus+counts.taxi;dom.window.close();
 }
 assert.equal(pages,47);assert.equal(records,6040); // 山北町の循環バス券を、山間部助成とは別の制度として追加。
 console.log('PASS: 47 generated prefectures / 6,040 records; local labels, all categories, multiple names, region AND, empty/reset, correct detail paths, unique IDs and tracking without input');
})().catch(error=>{console.error(error);process.exit(1)});
