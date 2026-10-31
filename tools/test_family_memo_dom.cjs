/* Real generated pages and handlers. External resources are never loaded.
   NODE_PATH=/tmp/jk-availability-test/node_modules node tools/test_family_memo_dom.cjs */
const {JSDOM}=require('jsdom');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'), tick=()=>new Promise(resolve=>setTimeout(resolve,10));
async function page(file, options={}) {
  const dom=new JSDOM(fs.readFileSync(path.join(root,file),'utf8'),{
    url:(options.local?'http://127.0.0.1:8847/':'https://jimotokurabe.jp/')+file+'?q=PRIVATE_QUERY#PRIVATE_HASH',
    runScripts:'outside-only',pretendToBeVisual:true});
  const w=dom.window, observers=[]; let copied='',denied=false;
  w.performance.getEntriesByType=()=>[];
  w.HTMLElement.prototype.scrollIntoView=()=>{};
  w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
  w.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new w.Event('close'));};
  w.navigator.clipboard={writeText:async text=>{if(denied)throw Error('denied');copied=text;}};
  w.IntersectionObserver=class {
    constructor(callback){this.callback=callback;this.targets=[];observers.push(this);}
    observe(target){this.targets.push(target);}
    unobserve(){}
  };
  if(options.saved)w.localStorage.setItem('jimoto-benefit-selection:https://jimotokurabe.jp/'+file,JSON.stringify(options.saved));
  if(options.blockStorage)Object.defineProperty(w,'localStorage',{get(){throw Error('blocked');}});
  for(const script of [...w.document.scripts]) {
    if(['application/json','application/ld+json'].includes(script.type))continue;
    if(script.src){const url=new URL(script.src);if(url.origin===w.location.origin)w.eval(fs.readFileSync(path.join(root,url.pathname),'utf8'));}
    else if(script.textContent.trim())w.eval(script.textContent);
  }
  await tick();
  return {w,dom,copied:()=>copied,deny:()=>{denied=true;},
    click:async selector=>{const element=w.document.querySelector(selector);assert.ok(element,selector);element.focus();element.click();await tick();},
    events:name=>Array.from(w.dataLayer||[],args=>Array.from(args)).filter(args=>args[0]==='event'&&(!name||args[1]===name)),
    expose:()=>observers.forEach(observer=>observer.callback(observer.targets.map(target=>({target,isIntersecting:true,intersectionRatio:.5}))))};
}
function assertRecordIncluded(h,id) {
  const record=h.w.document.querySelector('#record-'+id), text=h.w.document.querySelector('#selection-text').value;
  for(const link of record.querySelectorAll('a[href^="https:"]')) assert.ok(text.includes(link.href),'source retained: '+link.href);
  const dates=record.textContent.match(/20\d{2}(?:-\d{2}-\d{2}|年\d{1,2}月\d{1,2}日)/g)||[];
  for(const date of dates)assert.ok(text.includes(date),'date retained: '+date);
  for(const condition of record.querySelectorAll('dd, .important')) {
    const compact=s=>s.replace(/\s+/g,'');
    // Source URLs are inserted inside copied link labels, so check plain leaves.
    if(!condition.querySelector('a')&&condition.textContent.trim())assert.ok(compact(text).includes(compact(condition.textContent)),'condition retained');
  }
}
(async()=>{
  for(const file of ['hyogo-menkyo-henno/kobe.html','kanagawa-menkyo-henno/yokohama.html','hokkaido-menkyo-henno/sapporo.html','okinawa-menkyo-henno/ogimi.html']) {
    const h=await page(file,{saved:['support','invalid','support']});
    const d=h.w.document;
    assert.equal(h.events('family_memo_view').length,0,'no impression before visibility');
    h.expose();h.expose();
    assert.equal(h.events('family_memo_view').length,2,'once per entrance per page, not per panel');
    h.w.jkAnalytics.familyMemoViewed('PRIVATE_TEXT');h.w.jkAnalytics.familyMemoOpened('PRIVATE_TEXT');
    assert.equal(h.events('family_memo_view').length,2);assert.equal(h.events('family_memo_open').length,0);
    await h.click('[data-share-benefit=taxi]');
    assert.equal(d.querySelector('#selection-dialog').open,true);
    assert.equal(h.events('family_memo_open').at(-1)[2].entry_point,'support_panel');
    assertRecordIncluded(h,'taxi');
    assert.equal(d.querySelector('[data-add-family=taxi]').getAttribute('aria-pressed'),'false','single preview does not alter saved selection');
    assert.equal(d.querySelector('[data-add-family=support]').getAttribute('aria-pressed'),'true');
    await h.click('#selection-copy');assert.equal(h.events('memo_copy').length,1);assert.equal(h.copied(),d.querySelector('#selection-text').value);
    h.deny();await h.click('#selection-copy');assert.equal(h.events('memo_copy').length,1,'failed copy is not success');
    assert.ok(d.querySelector('#selection-copy-status').textContent.includes('手動'));
    await h.click('#selection-close');assert.equal(d.activeElement.dataset.shareBenefit,'taxi','close restores the actual opener');
    await h.click('[data-add-family=taxi]');
    assert.ok(d.querySelector('[data-selected-summary]').textContent.includes('2項目'));
    const stored=JSON.parse(h.w.localStorage.getItem('jimoto-benefit-selection:https://jimotokurabe.jp/'+file));
    assert.deepEqual(stored,['support','taxi']);
    assert.equal(d.querySelector('#selected-benefits [data-share-city]')!==null,true,'copy beside saved items');
    await h.click('[data-share-city]');assertRecordIncluded(h,'support');assertRecordIncluded(h,'taxi');
    assert.equal(h.events('family_memo_open').at(-1)[2].entry_point,'family_section');
    await h.click('#selection-close');assert.ok(d.activeElement.matches('[data-share-city]'));
    await h.click('[data-add-family=taxi]');assert.equal(d.querySelector('[data-add-family=taxi]').getAttribute('aria-pressed'),'false');
    assert.ok(!JSON.stringify(h.events()).includes('PRIVATE_'),'query, hash and unknown strings never sent');
    h.dom.window.close();
    const restored=await page(file,{saved:stored});
    assert.ok(restored.w.document.querySelector('[data-selected-summary]').textContent.includes('2項目'));
    restored.dom.window.close();
  }
  const blocked=await page('hyogo-menkyo-henno/kobe.html',{blockStorage:true});
  await blocked.click('[data-add-family=benefit]');assert.ok(blocked.w.document.querySelector('#selected-status').textContent.includes('開いている間'));
  await blocked.click('[data-share-city]');assert.equal(blocked.w.document.querySelector('#selection-dialog').open,true);blocked.dom.window.close();
  const empty=await page('hyogo-menkyo-henno/kobe.html');
  await empty.click('[data-share-city]');assert.equal(empty.w.document.querySelector('#warm-share-dialog').open,true,'existing page-guide fallback');empty.dom.window.close();
  const local=await page('hyogo-menkyo-henno/kobe.html',{local:true});
  local.expose();await local.click('[data-share-benefit=benefit]');await local.click('#selection-copy');
  assert.ok(local.copied().includes('2023'));assert.equal(local.events().length,0);local.dom.window.close();
  console.log('PASS: single/support group previews, full conditions/sources/dates, storage restore/blocking, actual focus return, copy success/failure, visible-only deduplicated telemetry, unknown parameters rejected, local GA off');
})().catch(error=>{console.error(error);process.exit(1);});
