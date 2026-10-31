/* Generated page and real scripts; no external resources or GA requests. */
const {JSDOM}=require('jsdom'), fs=require('node:fs'), path=require('node:path'), assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const dom=new JSDOM(fs.readFileSync(path.join(root,'hyogo-menkyo-henno.html'),'utf8'),{url:'https://jimotokurabe.jp/hyogo-menkyo-henno.html?q=PRIVATE_QUERY',runScripts:'outside-only',pretendToBeVisual:true});
const w=dom.window,d=w.document;
w.performance.getEntriesByType=()=>[];w.HTMLElement.prototype.scrollIntoView=()=>{};
for(const script of [...d.scripts]){
 if(['application/json','application/ld+json'].includes(script.type))continue;
 if(script.src){const url=new URL(script.src);if(url.origin===w.location.origin)w.eval(fs.readFileSync(path.join(root,url.pathname),'utf8'));}
 else if(script.textContent.trim())w.eval(script.textContent);
}
const visible=()=>[...d.querySelectorAll('[data-comparison-row]')].filter(row=>!row.hidden&&!row.closest('[data-comparison-kind]').hidden);
const events=name=>Array.from(w.dataLayer||[],args=>Array.from(args)).filter(args=>args[0]==='event'&&(!name||args[1]===name));
const input=d.querySelector('#city-query'),area=d.querySelector('#area');
function query(text){input.value=text;input.dispatchEvent(new w.Event('input'));}
function kind(value){const radio=d.querySelector(`[name="comparison-kind"][value="${value}"]`);radio.checked=true;radio.dispatchEvent(new w.Event('change'));}
(async()=>{
 await new Promise(resolve=>setTimeout(resolve,10));
 assert.equal(visible().length,41);assert.ok(visible().every(row=>row.closest('[data-comparison-kind]').dataset.comparisonKind==='return'));
 kind('bus');assert.equal(visible().length,54,'all 45 programs plus 9 status rows');
 kind('taxi');assert.equal(visible().length,41);
 kind('all');assert.equal(visible().length,136);
 query('神戸、アカシ');assert.equal(new Set(visible().map(row=>row.dataset.city)).size,2);
 assert.ok(visible().every(row=>['kobe','akashi'].includes(row.dataset.city)));
 query('　こうべ　明石 ');assert.equal(new Set(visible().map(row=>row.dataset.city)).size,2);
 area.value='higashi-harima';area.dispatchEvent(new w.Event('change'));
 assert.ok(visible().every(row=>row.dataset.city==='akashi'),'area AND names');
 input.dispatchEvent(new w.CompositionEvent('compositionstart'));input.value='PRIVATE_SEARCH';input.dispatchEvent(new w.Event('input'));
 assert.ok(visible().length,'IME composition waits');input.dispatchEvent(new w.CompositionEvent('compositionend'));
 assert.equal(visible().length,0);assert.equal(d.querySelector('#comparison-empty').hidden,false);
 d.querySelector('#reset').click();assert.equal(visible().length,136);assert.equal(area.value,'');assert.equal(input.value,'');
 kind('return');query('川西');
 assert.ok(visible()[0].textContent.includes('予算'));assert.ok(visible()[0].textContent.includes('1人1回'));
 d.querySelector('#filter-form').dispatchEvent(new w.Event('submit',{cancelable:true}));assert.equal(d.activeElement.id,'comparison-title');
 const detail=visible()[0].querySelector('details');assert.equal(detail.open,false);
 w.dispatchEvent(new w.Event('beforeprint'));assert.equal(detail.open,true);w.dispatchEvent(new w.Event('afterprint'));assert.equal(detail.open,false);
 d.querySelector('#reset').click();
 w.location.hash='#comparison-bus';w.dispatchEvent(new w.HashChangeEvent('hashchange'));assert.equal(visible().length,54);
 const legacy=d.querySelector('#municipal-directory [id]');assert.ok(legacy,'retained legacy anchor');
 const directory=d.querySelector('#municipal-directory');directory.open=false;
 w.location.hash='#'+legacy.id;w.dispatchEvent(new w.HashChangeEvent('hashchange'));assert.equal(directory.open,true,'old city links reveal directory');
 const source=d.querySelector('.pref-comparison [data-official-source]');source.addEventListener('click',event=>event.preventDefault());source.click();
 assert.equal(events('official_info_click').length,1);
 const city=d.querySelector('.pref-comparison .comparison-detail');city.addEventListener('click',event=>event.preventDefault());city.click();
 assert.equal(events('related_support_click').length,1);
 assert.ok(!JSON.stringify(events()).includes('PRIVATE_'),'search and query not sent');
 const ids=[...d.querySelectorAll('[id]')].map(el=>el.id);assert.equal(ids.length,new Set(ids).size,'unique IDs');
 dom.window.close();
 console.log('PASS: 41/54/41 complete records, multiple names/kana, region AND, IME, zero/reset, form focus, disclosures/print restoration, old anchors, existing analytics without search values');
})().catch(error=>{console.error(error);process.exit(1)});
