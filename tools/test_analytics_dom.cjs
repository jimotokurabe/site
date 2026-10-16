/* npm install --prefix /tmp/jk-analytics-test jsdom@30.1.3 --no-audit --no-fund
   NODE_PATH=/tmp/jk-analytics-test/node_modules node tools/test_analytics_dom.cjs
   No resources loader: Google tag and all external requests remain inert. */
const {JSDOM}=require('jsdom'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const tick=()=>new Promise(r=>setTimeout(r,10));
async function page(file,opts={}) {
 const dom=new JSDOM(fs.readFileSync(path.join(root,file),'utf8'),{url:(opts.local?'http://127.0.0.1:8847/':'https://jimotokurabe.jp/')+file+(opts.query||''),runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window;let copyOK=true,legacyOK=false,copied='';
 w.performance.getEntriesByType=()=>[];w.scrollTo=()=>{}; w.print=()=>{};w.HTMLElement.prototype.scrollIntoView=()=>{};w.HTMLDialogElement.prototype.showModal=function(){this.open=true};w.HTMLDialogElement.prototype.close=function(){this.open=false};
 Object.defineProperty(w,'isSecureContext',{value:true});
 w.navigator.clipboard={writeText:async text=>{if(!copyOK)throw Error('denied');copied=text;}};
 w.document.execCommand=()=>legacyOK;
 w.fetch=async url=>{if(opts.failFetch || (opts.failCatalog && String(url).endsWith('/hyogo.json')))throw Error('network');return {ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join(root,new URL(url,w.location).pathname),'utf8'))};};
 for(const script of [...w.document.scripts]) {
  if(script.type==='application/ld+json'||script.type==='application/json')continue;
  if(script.src){const u=new URL(script.src);if(u.origin===w.location.origin){w.eval(fs.readFileSync(path.join(root,u.pathname),'utf8'));if(opts.invalidEstimate && u.pathname.endsWith('transport-cost-engine.js')) w.TransportCost.estimate=()=>null;}}
  else if(script.textContent.trim())w.eval(script.textContent);
 }
 await tick();await tick();
 return {w,dom,events:name=>Array.from(w.dataLayer||[],a=>Array.from(a)).filter(a=>a[0]==='event'&&(!name||a[1]===name)),
 click:async selector=>{const el=w.document.querySelector(selector);assert.ok(el,selector);el.click();await tick();},deny(){copyOK=false;},legacy(){legacyOK=true;},copied:()=>copied};
}
(async()=>{
 // Every copy implementation is exercised through its real DOM handler, both outcomes.
 const cases=[['hyogo-menkyo-henno/nishinomiya.html','#selection-copy','selected_supports'],['hyogo-gomi-support/kobe.html','[data-gomi-copy]','gomi_consultation'],['outing-plan.html','#outing-copy','outing_plan'],['transport-cost.html','#tc-copy','transport_cost']];
 for(const [file,selector,feature] of cases){
  const h=await page(file,file==='transport-cost.html'?{query:'?pref=hyogo&city=nishinomiya'}:{});
  const memo=h.w.document.querySelector('#selection-memo, #outing-memo');if(memo)memo.value='PRIVATE_MEMO_相談本文';
  await h.click(selector);assert.ok(!JSON.stringify(h.events()).includes('PRIVATE_MEMO'));assert.equal(h.events('memo_copy').length,1,file);assert.equal(h.events('memo_copy')[0][2].feature_type,feature);
  h.deny();await h.click(selector);assert.equal(h.events('memo_copy').length,1,file+' rejected copy');
  if(feature==='gomi_consultation'){h.legacy();await h.click(selector);assert.equal(h.events('memo_copy').length,2,'fallback success once');}
  h.dom.window.close();
 }
 const guide=await page('henno-hanashikata.html');await guide.click('[data-go=quiz]');for(let n=0;n<6;n++)await guide.click('#hk-opts button');await guide.click('.hk-phrase');assert.equal(guide.events('memo_copy').length,1);guide.deny();await guide.click('.hk-phrase');assert.equal(guide.events('memo_copy').length,1);assert.ok(guide.w.document.querySelector('.hk-phrase').textContent.includes('コピーできません'));guide.dom.window.close();
 const family=await page('index.html');await family.click('[data-family-copy]');assert.equal(family.events('memo_copy').length,1);family.deny();await family.click('[data-family-memo]');assert.equal(family.events('memo_copy').length,1);family.legacy();await family.click('[data-family-memo]');assert.equal(family.events('memo_copy').length,2);family.dom.window.close();
 const shared=await page('hyogo-menkyo-henno/nishinomiya.html');
 const trigger=shared.w.document.querySelector('[data-share-city]');assert.ok(trigger);trigger.click();await tick();await shared.click('[data-share-copy]');assert.equal(shared.events('memo_copy').length,1);shared.deny();await shared.click('[data-share-copy]');assert.equal(shared.events('memo_copy').length,1);shared.dom.window.close();
 const t=await page('transport-cost.html',{query:'?pref=hyogo&city=nishinomiya&q=PRIVATE_SEARCH#PRIVATE_HASH'});
 assert.equal(t.events('transport_estimate_view').length,1);assert.equal(t.w.document.querySelector('#tc-estimate').hidden,false);
 for(const value of [1000,3000,2000,1000])await t.click('#tc-fares button[data-value="'+value+'"]');
 await t.click('#tc-trips button[data-value="8"]');assert.equal(t.events('transport_estimate_view').length,1,'re-renders do not count as new use');
 assert.ok(!JSON.stringify(t.events()).includes('PRIVATE_'));t.dom.window.close();
 const unsupported=await page('transport-cost.html',{query:'?pref=okinawa&city=ogimi'});assert.equal(unsupported.events('transport_estimate_view').length,0);assert.equal(unsupported.events('transport_region_view')[0][2].estimate_status,'unsupported');assert.equal(unsupported.w.document.querySelector('#tc-estimate').hidden,true);unsupported.dom.window.close();
 const invalid=await page('transport-cost.html',{query:'?pref=hyogo&city=DOES_NOT_EXIST'});assert.equal(invalid.events('transport_estimate_view').length,0);assert.equal(invalid.events('transport_region_view').length,0);invalid.dom.window.close();
 const blank=await page('transport-cost.html');assert.equal(blank.events('transport_estimate_view').length,0);blank.dom.window.close();
 const bad=await page('transport-cost.html',{query:'?pref=hyogo&city=nishinomiya',invalidEstimate:true});assert.equal(bad.events('transport_estimate_view').length,0);assert.equal(bad.events('transport_region_view')[0][2].estimate_status,'error');assert.equal(bad.w.document.querySelector('#tc-estimate').hidden,true);bad.dom.window.close();
 const failedCatalog=await page('transport-cost.html',{query:'?pref=hyogo&city=nishinomiya',failCatalog:true});assert.equal(failedCatalog.events('transport_estimate_view').length,0);assert.equal(failedCatalog.events('transport_region_view')[0][2].estimate_status,'error');failedCatalog.dom.window.close();
 const error=await page('transport-cost.html',{failFetch:true});assert.equal(error.events('transport_estimate_view').length,0);error.dom.window.close();
 const local=await page('transport-cost.html',{local:true,query:'?pref=hyogo&city=nishinomiya'});await local.click('#tc-copy');assert.equal(local.events().length,0);assert.equal(local.w.document.querySelectorAll('script[src*="googletagmanager"]').length,0);assert.ok(local.copied().includes('西宮'));local.dom.window.close();
 console.log('PASS: actual page DOM/script integration, copy success/rejection/fallback, result/unsupported/invalid/error, repeated fare updates, local functionality without GA');
})().catch(e=>{console.error(e);process.exit(1)});
