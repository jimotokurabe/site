/* Execute the shipped tracker with controlled browser primitives; no network. */
const assert = require('node:assert/strict'), vm = require('node:vm'), fs = require('node:fs');
const code = fs.readFileSync('assets/analytics.js', 'utf8');
function harness({host='jimotokurabe.jp', protocol='https:', port='', noindex=false, disabled=false, canonical='https://jimotokurabe.jp/hyogo-menkyo-henno/nishinomiya.html', referrer='https://search.yahoo.co.jp/search?p=PRIVATE_SEARCH', loading=false}={}) {
  const events=[], scripts=[], listeners={};
  const window={};
  const document={title:'公開タイトル',referrer,readyState:loading?'loading':'complete',
    querySelector(s) { if(s.includes('noindex')) return noindex?{}:null; if(s==='link[rel="canonical"]')return {href:canonical};return {}; },
    addEventListener(type, fn) { listeners[type]=fn; }, createElement(){return {};}, head:{append(s){scripts.push(s);}}};
  const context={URL,Set,Date,location:{hostname:host,protocol,port,origin:protocol+'//'+host,href:protocol+'//'+host+'/page?secret=PRIVATE_INPUT#PRIVATE_HASH'}, document,window,localStorage:{getItem(){return disabled?'1':null;}}};
  vm.runInNewContext(code,context);
  function read(){return Array.from(window.dataLayer||[], args=>Array.from(args));}
  return {window,document,context,scripts,listeners,read,events:()=>read().filter(x=>x[0]==='event'), click(href, {source=false,inMain=true,print=false}={}) {
    const control={tagName:'A',matches(s){return s==='[data-official-source]'?source:print;},getAttribute(){return href;},closest(s){if(s==='main')return inMain?{}:null;return null;}};
    listeners.click?.({target:{closest:()=>control}});
  }};
}
for(const opts of [{host:'127.0.0.1'},{host:'localhost'},{host:'preview.example'},{host:'jimotokurabe.jp.example.com'},{protocol:'http:'},{port:'8443'},{noindex:true},{disabled:true}]) {
  const h=harness(opts);h.click('https://www.nishi.or.jp/');assert.equal(h.scripts.length,0);assert.equal(h.read().length,0);assert.equal(h.window.jkAnalytics,undefined);
}
const h=harness(); assert.equal(h.scripts.length,1); assert.equal(h.read().filter(x=>x[0]==='config').length,1);
assert.equal(h.read()[1][2].page_location,'https://jimotokurabe.jp/hyogo-menkyo-henno/nishinomiya.html');assert.equal(h.read()[1][2].page_referrer,'https://search.yahoo.co.jp/');
assert.equal(h.read()[1][2].page_type,'city_detail');assert.equal(h.read()[1][2].city_id,'hyogo:nishinomiya');
for(const url of ['https://www.nishi.or.jp/test?private=PRIVATE_LINK','https://www.npa.go.jp/test','https://www.city.amagasaki.hyogo.jp/test'])h.click(url);
h.click('https://www.hanshin-bus.co.jp/test?private=PRIVATE_LINK',{source:true});
for(const url of ['https://nishi.or.jp.example.com/test','https://example.com/test','javascript:alert(1)'])h.click(url);
assert.equal(h.events().length,4);assert.ok(h.events().every(e=>e[1]==='official_info_click'&&!('link_path' in e[2])&&!('link_url' in e[2])));
h.click('https://www.npa.go.jp/test',{inMain:false});assert.equal(h.events().length,4);
h.window.jkAnalytics.memoCopied('PRIVATE_MEMO');assert.equal(h.events().length,4);
h.window.jkAnalytics.memoCopied('selected_supports');assert.equal(h.events().at(-1)[1],'memo_copy');
h.window.jkAnalytics.estimateShown();assert.equal(h.events().filter(e=>e[1]==='transport_estimate_view').length,0);
h.window.jkAnalytics.transportRegion('hyogo','nishinomiya','supported');for(let i=0;i<20;i++)h.window.jkAnalytics.estimateShown();
assert.equal(h.events().filter(e=>e[1]==='transport_estimate_view').length,1);
h.window.jkAnalytics.clearTransportRegion();h.window.jkAnalytics.estimateShown();
h.window.jkAnalytics.transportRegion('okinawa','ogimi','unsupported');h.window.jkAnalytics.estimateShown();
h.window.jkAnalytics.transportRegion('hyogo','akashi','error');h.window.jkAnalytics.estimateShown();
assert.equal(h.events().filter(e=>e[1]==='transport_estimate_view').length,1);
h.window.jkAnalytics.transportRegion('hyogo','nishinomiya','supported');h.window.jkAnalytics.estimateShown();assert.equal(h.events().filter(e=>e[1]==='transport_estimate_view').length,1);
h.window.jkAnalytics.transportRegion('hyogo','akashi','supported');h.window.jkAnalytics.estimateShown();assert.equal(h.events().filter(e=>e[1]==='transport_estimate_view').length,2);
assert.ok(!JSON.stringify(h.read()).includes('PRIVATE_'));
assert.equal(harness({referrer:'http://127.0.0.1:8888/private'}).read()[1][2].page_referrer,'');
const delayed=harness({loading:true});delayed.window.jkAnalytics.transportRegion('hyogo','akashi','supported');delayed.window.jkAnalytics.estimateShown();delayed.listeners.DOMContentLoaded();assert.equal(delayed.events().filter(e=>e[1]==='transport_estimate_view').length,1);
vm.runInNewContext(code,h.context);assert.equal(h.scripts.length,1);
console.log('PASS: production-only boot, URL privacy, source classification, copy enums, region/error/reset/re-render deduplication, single boot');
