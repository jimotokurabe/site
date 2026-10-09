/* Behavioral tests for the real planner script. No browser/network dependencies. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

class Element {
  constructor(tag = 'div') {
    this.tagName = tag; this.children = []; this.listeners = {}; this.attributes = {};
    this.value = ''; this.checked = false; this.hidden = false; this.disabled = false;
    this.validity = {valid: true}; this.selectedIndex = 0; this.textContent = '';
  }
  append(...children) { this.children.push(...children); if (this.tagName === 'select' && this.children.length === children.length) this.value = children[0]?.value || ''; }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  emit(type) { for (const fn of this.listeners[type] || []) fn({preventDefault() {}}); }
  setAttribute(key, value) { this.attributes[key] = value; }
  removeAttribute(key) { delete this.attributes[key]; }
  focus() {}
  reportValidity() {}
}
function fixture() {
  const elements = new Map();
  const get = name => {
    if (!elements.has(name)) elements.set(name, new Element(/(?:pref|city|support|mode|booking)$/.test(name) ? 'select' : 'div'));
    return elements.get(name);
  };
  const progress = new Element(); progress.children = [new Element(), new Element(), new Element()];
  const pending = [];
  const context = vm.createContext({URL, URLSearchParams, Map, Set, console,
    location: {href: 'https://jimotokurabe.jp/outing-plan.html', search: ''}, navigator: {},
    window: {addEventListener() {}, print() {}},
    document: {getElementById: get, createElement: tag => new Element(tag),
      querySelector: selector => selector === '.outing-progress' ? progress : null,
      querySelectorAll: selector => selector === '[data-step]' ? [new Element(), new Element(), new Element()] : []},
    fetch: url => new Promise((resolve, reject) => pending.push({url, resolve: data => resolve({ok: true, json: async () => data}), reject}))});
  const script = fs.readFileSync(path.join(__dirname, '../assets/outing-plan.js'), 'utf8')
    .replace('  app.hidden = false;', '  globalThis.testApi = {collect, setPref, selected, setIndex(data) {indexData = data;}}; app.hidden = false;');
  vm.runInContext(script, context);
  for (const key of ['out', 'back']) get('outing-' + key + '-mode').value = 'まだ決めていない';
  return {get: id => get('outing-' + id), api: context.testApi, pending};
}
const support = id => ({id, name: '支援' + id, type: 'bus', selectable: true, details: [], sources: [], checked: '2026-10-06'});
const flush = () => new Promise(resolve => setImmediate(resolve));

async function run() {
  {
    const {get, api} = fixture();
    const total = () => api.collect().groups[2][1][0][1];
    assert.match(total(), /未確認/);
    get('out-cost').value = '0'; get('back-cost').value = '0';
    assert.equal(total(), '0円', 'explicit zero must remain distinct from unknown');
    api.selected.set('a', {program: support('a'), ready: 'held'});
    api.selected.set('b', {program: support('b'), ready: 'held'});
    get('out-support').value = 'a'; get('back-support').value = 'b';
    get('out-cost').value = '100'; get('back-cost').value = '200';
    assert.match(total(), /合計しません/, 'two supports cannot total before a combination check');
    get('combination-confirmed').checked = true;
    assert.equal(total(), '300円');
    assert.match(api.collect().groups[2][1][0][0], /仮の往復費用/, 'held alone is not confirmation of this trip');
    get('out-confirmed').checked = true; get('back-confirmed').checked = true;
    get('out-mode').value = 'バス'; get('back-mode').value = 'バス';
    assert.doesNotMatch(api.collect().groups[2][1][0][0], /仮/);
    for (const field of ['out-cost', 'out-time']) {
      get('out-confirmed').checked = true; get(field).emit('input');
      assert.equal(get('out-confirmed').checked, false, field + ' edit invalidates its confirmation');
    }
    for (const field of ['place', 'day']) {
      get('out-confirmed').checked = true; get('back-confirmed').checked = true;
      get('combination-confirmed').checked = true; get(field).emit('input');
      assert.equal(get('out-confirmed').checked, false);
      assert.equal(get('back-confirmed').checked, false);
      assert.equal(get('combination-confirmed').checked, false);
    }
    get('combination-confirmed').checked = true;
    get('out-mode').emit('change');
    assert.equal(get('combination-confirmed').checked, false);
    assert.equal(get('out-cost').value, '');
    assert.equal(get('out-confirmed').checked, false);
    get('back-support').emit('change');
    assert.equal(get('back-cost').value, '');
    assert.equal(get('combination-confirmed').checked, false);
  }
  {
    const {get, api, pending} = fixture();
    pending.shift().resolve({prefectures: [{id: 'a', name: '県A'}, {id: 'b', name: '県B'}]});
    await flush();
    const a = api.setPref('a'); const aRequest = pending.shift();
    const b = api.setPref('b'); const bRequest = pending.shift();
    bRequest.resolve({cities: [{id: 'b-city', name: 'B市', programs: [], page: 'b/b.html'}]});
    await b;
    aRequest.resolve({cities: [{id: 'a-city', name: 'A市', programs: [], page: 'a/a.html'}]});
    await a;
    assert.equal(get('city').children[1].value, 'b-city', 'old prefecture response must not replace the new city choices');
    const old = api.setPref('a'); const oldRequest = pending.shift();
    await api.setPref('');
    oldRequest.resolve({cities: [{id: 'a-city', name: 'A市', programs: []}]}); await old;
    assert.equal(get('city').disabled, true, 'clearing the region must invalidate an older pending request');
    assert.equal(get('city').children.length, 1);
  }
  console.log('Planner behavior tests passed: unknown/zero, readiness, combination totals, reset events, stale requests.');
}
run().catch(error => { console.error(error); process.exitCode = 1; });
