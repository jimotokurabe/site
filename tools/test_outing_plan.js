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
    this.className = '';
    this.classList = {
      contains: name => this.className.split(/\s+/).includes(name),
      toggle: (name, force) => {
        const names = new Set(this.className.split(/\s+/).filter(Boolean));
        const active = force === undefined ? !names.has(name) : force;
        if (active) names.add(name); else names.delete(name);
        this.className = [...names].join(' ');
        return active;
      },
      add: (...names) => names.forEach(name => this.classList.toggle(name, true)),
      remove: (...names) => names.forEach(name => this.classList.toggle(name, false))
    };
  }
  append(...children) { this.children.push(...children); if (this.tagName === 'select' && this.children.length === children.length) this.value = children[0]?.value || ''; }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  emit(type) { for (const fn of this.listeners[type] || []) fn({target: this, currentTarget: this, preventDefault() {}}); }
  setAttribute(key, value) { this.attributes[key] = value; }
  removeAttribute(key) { delete this.attributes[key]; }
  get firstElementChild() { return this.children[0] || null; }
  focus() { Element.activeElement = this; }
  reportValidity() {}
}
function fixture() {
  const elements = new Map();
  const get = name => {
    if (!elements.has(name)) elements.set(name, new Element(/(?:pref|city|support|mode|booking)$/.test(name) ? 'select' : 'div'));
    return elements.get(name);
  };
  const progress = new Element(); progress.children = [new Element(), new Element(), new Element()];
  const purposes = ['通院', '買い物', '趣味・人に会う', 'その他'].map(value => {
    const input = new Element('input'); input.value = value; return input;
  });
  const next = new Element('button');
  const pending = [];
  const context = vm.createContext({URL, URLSearchParams, Map, Set, console,
    location: {href: 'https://jimotokurabe.jp/outing-plan.html', search: ''}, navigator: {},
    window: {addEventListener() {}, print() {}},
    document: {getElementById: get, createElement: tag => new Element(tag),
      querySelector: selector => selector === '.outing-progress' ? progress : selector === 'input[name="purpose"]:checked' ? purposes.find(input => input.checked) || null : null,
      querySelectorAll: selector => selector === '[data-step]' ? [new Element(), new Element(), new Element()] : selector === 'input[name="purpose"]' ? purposes : selector === '[data-next]' ? [next] : []},
    fetch: url => new Promise((resolve, reject) => pending.push({url, resolve: data => resolve({ok: true, json: async () => data}), reject}))});
  const script = fs.readFileSync(path.join(__dirname, '../assets/outing-plan.js'), 'utf8')
    .replace('  app.hidden = false;', '  globalThis.testApi = {collect, setPref, setCity, selected, amount, normalCost, comparison, normalizePlace, cityMatches, cityInitial, renderCityChoices, setIndex(data) {indexData = data;}}; app.hidden = false;');
  vm.runInContext(script, context);
  for (const key of ['out', 'back']) get('outing-' + key + '-mode').value = 'まだ決めていない';
  return {get: id => get('outing-' + id), api: context.testApi, pending, purposes, next};
}
const support = id => ({id, name: '支援' + id, type: 'bus', selectable: true, details: [], sources: [], checked: '2026-10-06'});
const flush = () => new Promise(resolve => setImmediate(resolve));

async function run() {
  {
    const {get, api} = fixture();
    get('monthly-trips').value = '4';
    get('out-cost').value = '200'; get('back-cost').value = '300';
    get('finish').emit('click');
    assert.equal(api.comparison().enabled, false, 'ordinary monthly planning requires no support');
    assert.equal(api.comparison().planned, 500);
    assert.equal(api.comparison().monthlyPlanned, 2000);
    assert.equal(get('result-overview').children[1].children[1].textContent, '500円');
    assert.equal(get('result-comparison').hidden, false);
    assert.equal(get('result-comparison').children[1].textContent, '月4回：2,000円');
    assert.ok(get('memo').value.includes('月4回：2,000円'), 'copy retains the same ordinary monthly total');
    get('back-cost').value = ''; get('finish').emit('click');
    assert.equal(api.comparison().monthlyPlanned, null);
    assert.match(get('result-comparison').children[1].textContent, /未確認/);
    assert.ok(get('memo').value.includes('月4回：未確認'), 'missing fare must not be treated as free');
    get('out-cost').value = '0'; get('back-cost').value = '0'; get('finish').emit('click');
    assert.equal(get('result-comparison').children[1].textContent, '月4回：0円');
    assert.ok(get('memo').value.includes('月4回：0円'));
    get('monthly-trips').value = ''; get('finish').emit('click');
    assert.equal(get('result-comparison').hidden, true, 'monthly section is optional');
    assert.ok(!get('memo').value.includes('【続けた場合の交通費】'));
  }
  {
    const {get, api, purposes, next} = fixture();
    const destination = '<img src=x onerror=alert(1)>病院';
    get('place').value = destination;
    for (const [purpose, hint] of [['通院', /診察が長引いても/], ['買い物', /荷物を持って/], ['趣味・人に会う', /最終便/]]) {
      purposes.forEach(input => { input.checked = input.value === purpose; });
      purposes.find(input => input.checked).emit('change');
      assert.match(get('purpose-hint').textContent, hint, 'purpose change explains the relevant return-trip concern');
    }
    next.emit('click');
    assert.equal(get('trip-context').textContent, '家 → ' + destination + ' → 家');
    assert.match(get('trip-hint').textContent, /最終便/);
    assert.equal(get('trip-context').children.length, 0, 'destination remains text, not HTML');
    get('out-mode').value = 'バス'; get('back-mode').value = 'タクシー';
    get('out-time').value = '9時の便'; get('back-time').value = '診察後に呼ぶ';
    get('out-cost').value = '0';
    let plan = api.collect();
    assert.equal(plan.day, '日程はこれから相談');
    assert.equal(plan.checks[0], '帰りの交通費を確認する', 'undecided date does not block concrete transport planning');
    assert.ok(plan.checks.includes('日程が決まったら、その曜日・時間の便が使えるか確認する'));
    get('finish').emit('click');
    assert.equal(get('result-next').textContent, plan.checks[0]);
    assert.ok(get('memo').value.includes('まず確認すること：' + plan.checks[0]));
    assert.ok(get('memo').value.includes('行き先：' + destination));
    assert.equal(get('result-route').textContent, '家 → ' + destination + ' → 家');
    const overview = get('result-overview').children;
    assert.equal(overview[0].children[1].textContent, 'バスで行き、タクシーで帰る案');
    assert.match(overview[1].children[1].textContent, /未確認/);
    get('back-cost').value = '0'; get('finish').emit('click');
    assert.equal(get('result-overview').children[1].children[1].textContent, '0円', 'explicit zero survives the result overview');
  }
  {
    const {api} = fixture();
    const city = {name: '神戸市', kana: 'こうべし'};
    for (const query of ['神戸', 'こうべ', 'コウベ', 'ｺｳﾍﾞ', '  こう べ　し  ']) {
      assert.equal(api.cityMatches(city, query), true, 'municipality search matches ' + query);
    }
    assert.equal(api.cityMatches(city, '京都'), false);
    assert.equal(api.cityMatches(city, ''), true);
    assert.equal(api.cityMatches({name: '神戸市'}, '神戸'), true, 'older catalog remains searchable by name');
    assert.equal(api.cityMatches({name: '神戸市'}, 'こうべ'), false, 'missing reading must not invent a match');
    assert.equal(api.normalizePlace(' Ａ ﾊﾟ　ン '), 'aぱん', 'search folds width, case, katakana and spaces');
    for (const [kana, expected] of [['あきたし', 'あ'], ['いこまし', 'あ'], ['がまごおりし', 'か'],
      ['ギフシ', 'か'], ['ざまし', 'さ'], ['ぢ', 'た'], ['ぬまづし', 'な'], ['ぱ', 'は'],
      ['ぼ', 'は'], ['む', 'ま'], ['ゆ', 'や'], ['れ', 'ら'], ['を', 'わ']]) {
      assert.equal(api.cityInitial({name: '市', kana}), expected, 'kana group for ' + kana);
    }
  }
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
    const {get, api} = fixture();
    const assign = (key, id = 'a', ready = 'held') => {
      api.selected.set(id, {program: support(id), ready});
      get(key + '-support').value = id;
    };
    const fare = (key, planned, normal) => {
      get(key + '-cost').value = planned;
      get(key + '-normal-cost').value = normal;
    };
    get('out-cost').value = '0';
    assert.equal(api.amount('out-cost'), 0);
    get('out-cost').value = '';
    assert.equal(api.amount('out-cost'), null);
    get('out-cost').value = '100'; get('out-cost').validity.valid = false;
    assert.equal(api.amount('out-cost'), null, 'invalid fare must not be used');
    get('out-cost').validity.valid = true;
    for (const invalid of ['-1', '1.5', '1000001', 'NaN', 'Infinity', ' ']) {
      get('out-cost').value = invalid;
      assert.equal(api.amount('out-cost'), null, 'fare rejects ' + JSON.stringify(invalid));
    }
    fare('out', '100', '500'); fare('back', '200', '900');
    get('monthly-trips').value = '4'; get('monthly-confirmed').checked = true;
    assert.equal(api.normalCost('out'), 100, 'unassigned legs use the entered fare as their baseline');
    assert.equal(api.comparison().enabled, false);
    assert.equal(api.comparison().difference, null);
    assert.equal(api.comparison().monthlyDifference, null, 'no support means no claimed saving');
    assign('out');
    let result = api.comparison();
    assert.equal(result.enabled, true);
    assert.equal(result.normal, 700, 'a stale hidden normal fare on an unsupported leg must not inflate savings');
    assert.equal(result.planned, 300);
    assert.equal(result.difference, 400);
    assert.equal(result.monthlyNormal, 2800);
    assert.equal(result.monthlyPlanned, 1200);
    assert.equal(result.monthlyDifference, 1600);
    assert.equal(result.provisional, true, 'held support still requires confirmation for this trip');
    get('out-confirmed').checked = true; get('out-mode').value = 'バス';
    assert.equal(api.comparison().provisional, false);
    get('monthly-confirmed').checked = false;
    result = api.comparison();
    assert.equal(result.monthlyPending, true);
    assert.equal(result.monthlyNormal, 2800, 'normal monthly cost is independent of support availability');
    assert.equal(result.monthlyPlanned, null);
    assert.equal(result.monthlyDifference, null);
    get('monthly-confirmed').checked = true;
    for (const invalid of ['', '0', '-1', '1.5', '101', 'NaN', 'Infinity']) {
      get('monthly-trips').value = invalid;
      result = api.comparison();
      assert.equal(result.count, null, 'monthly count rejects ' + JSON.stringify(invalid));
      assert.equal(result.monthlyNormal, null);
      assert.equal(result.monthlyPlanned, null);
      assert.equal(result.monthlyDifference, null);
    }
    for (const valid of ['1', '100']) {
      get('monthly-trips').value = valid;
      assert.equal(api.comparison().count, Number(valid));
    }
    get('monthly-trips').value = '4'; get('monthly-trips').validity.valid = false;
    assert.equal(api.comparison().count, null, 'browser-invalid monthly count is not multiplied');
    get('monthly-trips').validity.valid = true;
    fare('out', '0', '0'); fare('back', '0', '');
    result = api.comparison();
    assert.equal(result.normal, 0); assert.equal(result.planned, 0);
    assert.equal(result.difference, 0); assert.equal(result.monthlyDifference, 0);
    fare('out', '500', '100'); fare('back', '200', '900');
    assert.equal(api.comparison().difference, -400, 'a more expensive plan must not become zero savings');
    assert.equal(api.comparison().monthlyDifference, -1600);
    get('out-normal-cost').value = '';
    result = api.comparison();
    assert.equal(result.normal, null); assert.equal(result.difference, null);
    assert.equal(result.monthlyNormal, null);
    assert.equal(result.planned, 700, 'missing baseline does not erase the entered plan cost');
    get('out-normal-cost').value = '500'; get('back-cost').value = '';
    result = api.comparison();
    assert.equal(result.normal, null); assert.equal(result.planned, null);
    assert.equal(result.difference, null, 'one missing leg prevents a round-trip difference');
    fare('back', '200', '900'); assign('back', 'b');
    result = api.comparison();
    assert.equal(result.blocked, true);
    assert.equal(result.normal, 1400);
    assert.equal(result.monthlyNormal, 5600);
    assert.equal(result.planned, null); assert.equal(result.monthlyPlanned, null);
    assert.equal(result.difference, null); assert.equal(result.monthlyDifference, null);
    get('combination-confirmed').checked = true;
    assert.equal(api.comparison().planned, 700);
    assert.equal(api.comparison().difference, 700);
    assign('back', 'a', 'applying');
    get('combination-confirmed').checked = false;
    assert.equal(api.comparison().blocked, false, 'one shared support needs no two-program combination check');
    assert.equal(api.comparison().provisional, true, 'hypothetical postapproval costs remain provisional');
    assert.equal(api.comparison().monthlyPlanned, 2800, 'confirmed hypothetical monthly usage may be compared');
    get('finish').emit('click');
    assert.match(get('memo').value, /【交通費の比較】/);
    assert.match(get('memo').value, /通常の月額：5,600円/);
    assert.match(get('memo').value, /支援利用後の月額：2,800円/);
    assert.match(get('memo').value, /申請・条件確認後の仮の計画/);
    get('monthly-confirmed').checked = false;
    get('finish').emit('click');
    assert.match(get('memo').value, /支援利用後の月額：券の残数・利用上限等が未確認/);
    assert.match(get('memo').value, /月の差額：未確認/);
    for (const field of ['out-cost', 'out-time', 'back-cost', 'back-time']) {
      get('monthly-confirmed').checked = true;
      get(field.replace(/-(cost|time)$/, '-confirmed')).checked = true;
      get(field).emit('input');
      assert.equal(get('monthly-confirmed').checked, false, field + ' edit invalidates monthly usage');
      assert.equal(get(field.replace(/-(cost|time)$/, '-confirmed')).checked, false);
    }
    for (const key of ['out', 'back']) {
      get(key + '-confirmed').checked = true;
      get('monthly-confirmed').checked = true;
      get(key + '-normal-cost').emit('input');
      assert.equal(get('monthly-confirmed').checked, false);
      assert.equal(get(key + '-confirmed').checked, true, 'baseline-only edit keeps trip confirmation');
    }
    for (const field of ['monthly-trips', 'place', 'day']) {
      get('monthly-confirmed').checked = true;
      get(field).emit('input');
      assert.equal(get('monthly-confirmed').checked, false, field + ' edit invalidates monthly usage');
    }
    get('monthly-confirmed').checked = true;
    get('combination-confirmed').emit('change');
    assert.equal(get('monthly-confirmed').checked, false);
    for (const field of ['out-mode', 'back-support']) {
      const key = field.split('-')[0];
      fare(key, '100', '500');
      get('monthly-confirmed').checked = true;
      get(field).emit('change');
      assert.equal(get(key + '-cost').value, '');
      assert.equal(get(key + '-normal-cost').value, '', 'changed route/support clears both fares');
      assert.equal(get('monthly-confirmed').checked, false);
    }
    fare('out', '100', '500'); get('monthly-confirmed').checked = true;
    await api.setPref('');
    assert.equal(get('out-cost').value, '');
    assert.equal(get('out-normal-cost').value, '');
    assert.equal(get('monthly-confirmed').checked, false, 'region change invalidates monthly usage');
    assert.equal(api.comparison().enabled, false);
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
  {
    const {get, api, pending} = fixture();
    const button = (id, label) => {
      const found = get(id).children.find(child => child.textContent === label);
      assert.ok(found, id + ' has choice ' + label);
      return found;
    };
    pending.shift().resolve({prefectures: [
      {id: 'hyogo', name: '兵庫県', region: '近畿'},
      {id: 'kyoto', name: '京都府', region: '近畿'},
      {id: 'tokyo', name: '東京都', region: '関東'}
    ]});
    await flush();
    assert.equal(get('pref-options').children.length, 0, 'prefecture choices follow a region choice');
    button('region-options', '近畿').emit('click');
    assert.equal(get('pref-options').children.length, 2);
    assert.equal(Element.activeElement, get('pref-options').children[0], 'region choice moves keyboard focus to its prefectures');
    button('pref-options', '兵庫県').emit('click');
    assert.equal(get('pref').value, 'hyogo', 'visible choice updates the native state');
    assert.equal(get('city-search').disabled, true, 'search stays disabled while loading');
    const cities = [{id: 'kobe', name: '神戸市', kana: 'こうべし', programs: [support('a')]},
      ...Array.from({length: 24}, (_, i) => ({id: 'city-' + i, name: '甲市' + i, kana: 'かし' + i, programs: []})),
      {id: 'akashi', name: '明石市', kana: 'あかしし', programs: []}];
    pending.shift().resolve({cities}); await flush();
    assert.equal(Element.activeElement, get('city-search'), 'loaded prefecture focuses the city search');
    assert.equal(get('city').children.length, 27, 'native city state retains all choices');
    assert.equal(get('city-results').children.length, 12, 'city buttons render one bounded page');
    assert.match(get('city-count').textContent, /26件中 1〜12件/);
    get('city-more').emit('click');
    assert.match(get('city-count').textContent, /13〜24件/);
    assert.equal(Element.activeElement, get('city-count'), 'pagination announces the result range');
    assert.equal(get('city-results').children.length, 12);
    get('city-more').emit('click');
    assert.equal(get('city-results').children.length, 2);
    assert.equal(get('city-more').hidden, true);
    get('city-prev').emit('click');
    assert.match(get('city-count').textContent, /13〜24件/);
    get('city-search').value = 'ｺｳﾍﾞ'; get('city-search').emit('input');
    assert.match(get('city-count').textContent, /1件中 1〜1件/);
    button('city-results', '神戸市').emit('click');
    assert.equal(get('city').value, 'kobe');
    assert.equal(get('picker-body').hidden, true);
    assert.match(get('picker-summary').textContent, /兵庫県 神戸市/);
    assert.equal(Element.activeElement, get('picker-summary'), 'selected city summary receives focus outside the closed picker');
    assert.equal(get('picker-toggle').attributes['aria-expanded'], 'false');
    const choice = {program: support('a'), ready: 'held'};
    api.selected.set('a', choice); get('out-support').value = 'a';
    get('out-cost').value = '100'; get('out-normal-cost').value = '500';
    get('out-confirmed').checked = true; get('monthly-confirmed').checked = true;
    const preservesPlan = () => {
      assert.equal(api.selected.get('a'), choice, 'browsing must preserve selected support and readiness');
      assert.equal(get('out-support').value, 'a');
      assert.equal(get('out-cost').value, '100');
      assert.equal(get('out-normal-cost').value, '500');
      assert.equal(get('out-confirmed').checked, true);
      assert.equal(get('monthly-confirmed').checked, true);
    };
    get('picker-toggle').emit('click'); preservesPlan();
    assert.equal(get('picker-body').hidden, false);
    get('city-reset').emit('click'); preservesPlan();
    button('city-initials', 'あ行').emit('click'); preservesPlan();
    assert.equal(get('city-results').children.length, 1);
    assert.equal(get('city-results').children[0].textContent, '明石市');
    get('city-search').value = '甲'; get('city-search').emit('input'); preservesPlan();
    assert.equal(get('city-results').children.length, 12, 'typing clears the previous kana filter');
    get('city-more').emit('click'); preservesPlan();
    button('region-options', '関東').emit('click'); preservesPlan();
    button('region-options', '近畿').emit('click'); preservesPlan();
    button('pref-options', '兵庫県').emit('click'); preservesPlan();
    get('city-search').value = '見つからない市'; get('city-search').emit('input'); preservesPlan();
    assert.equal(get('city-results').children.length, 0);
    assert.match(get('city-count').textContent, /見つかりません/);
    get('city-reset').emit('click');
    button('city-results', '神戸市').emit('click'); preservesPlan();
    get('picker-toggle').emit('click');
    button('city-initials', 'あ行').emit('click');
    button('city-results', '明石市').emit('click');
    assert.equal(api.selected.size, 0, 'changing the actual municipality clears its support selections');
    assert.equal(get('out-cost').value, '');
    assert.equal(get('out-normal-cost').value, '');
    assert.equal(get('monthly-confirmed').checked, false);
    api.selected.set('a', choice); get('out-support').value = 'a'; get('out-cost').value = '100';
    get('picker-toggle').emit('click'); button('pref-options', '京都府').emit('click');
    assert.equal(api.selected.size, 0, 'changing the actual prefecture clears its support selections');
    assert.equal(get('out-cost').value, '');
    pending.shift().resolve({cities: []}); await flush();
    get('picker-clear').emit('click');
    assert.equal(get('pref').value, '');
    assert.equal(get('city').disabled, true);
    assert.equal(get('city-search').disabled, true);
    assert.equal(get('picker-body').hidden, false);
  }
  console.log('Planner behavior tests passed: unknown/zero, readiness, combination totals, reset events, stale requests, fare comparisons, monthly limits, kana search, paged region choices and browsing-state preservation.');
}
run().catch(error => { console.error(error); process.exitCode = 1; });
