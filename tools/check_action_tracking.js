// Exercise the shipped tracker without sending analytics or loading a browser.
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const html = fs.readFileSync('hyogo-menkyo-henno/nishinomiya.html', 'utf8');
const scripts = [...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(x => x[1]);
const code = scripts.find(s => s.includes('official_info_click'));
assert.ok(code);
function harness(hostname = 'jimotokurabe.jp') {
  let click; const events = [];
  vm.runInNewContext(code, {URL, location: {hostname, origin: `https://${hostname}`, href: `https://${hostname}/test.html`, pathname: '/test.html'}, document: {addEventListener: (type, fn) => {click = fn;}}, window: {gtag: (...args) => events.push(args)}});
  return {events, click(href, inMain = true) { if (!click) return; const control = {tagName: 'A', matches: () => false, getAttribute: () => href, closest: s => s === 'main' && inMain ? {} : null}; click({target: {closest: () => control}}); }};
}
for (const href of ['https://www.nishi.or.jp/test?private=1#x', 'https://www.city.yokohama.lg.jp/test', 'https://www.npa.go.jp/test', 'https://www.city.amagasaki.hyogo.jp/test', 'https://www.town.example.hokkaido.jp/test']) {
  const h = harness(); h.click(href); assert.equal(h.events.length, 1); assert.equal(h.events[0][1], 'official_info_click'); assert.equal(h.events[0][2].link_path, '/test'); assert.ok(!JSON.stringify(h.events).includes('private'));
}
for (const href of ['https://nishi.or.jp.example.com/test', 'https://fake-nishi.or.jp/test', 'https://city.amagasaki.hyogo.jp.example.com/test', 'https://example.com', '#support', 'javascript:alert(1)']) {
  const h = harness(); h.click(href); assert.equal(h.events.length, 0, href);
}
const local = harness('127.0.0.1'); local.click('https://www.nishi.or.jp/test'); assert.equal(local.events.length, 0);
const footer = harness(); footer.click('https://www.nishi.or.jp/test', false); assert.equal(footer.events.length, 0);
console.log('PASS: official domains, exclusions, privacy and local preview suppression');
