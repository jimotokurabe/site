/* Plan fields stay in this document. Only public regional catalogs are fetched. */
(() => {
  'use strict';
  const app = document.getElementById('outing-app');
  if (!app) return;
  const $ = id => document.getElementById('outing-' + id);
  const steps = Array.from(document.querySelectorAll('[data-step]'));
  const progress = document.querySelector('.outing-progress');
  let step = 0;
  const value = id => $(id).value.trim();
  const shown = id => value(id) || '未確認';
  const mode = key => value(key + '-mode') === 'まだ決めていない' ? '未定' : value(key + '-mode');
  const yen = number => number.toLocaleString('ja-JP') + '円';
  function amount(id, max = 1000000, min = 0) {
    const input = $(id), number = Number(input.value);
    return input.value.trim() !== '' && input.validity.valid && Number.isInteger(number) && number >= min && number <= max ? number : null;
  }
  function cost(key) { return amount(key + '-cost'); }
  function costText(key) { const number = cost(key); return number === null ? '未確認' : yen(number); }
  function validateCosts() {
    const ids = ['out-cost', 'back-cost', 'monthly-trips', ...legs.filter(key => programForLeg(key)).map(key => key + '-normal-cost')];
    for (const id of ids) {
      const input = $(id);
      if (!input.validity.valid) {
        showStep(1);
        if (id === 'monthly-trips') input.closest('details').open = true;
        input.reportValidity(); return false;
      }
    }
    return true;
  }
  function showStep(index) {
    step = index;
    $('result').hidden = true;
    $('form').hidden = false;
    progress.hidden = false;
    steps.forEach((node, i) => { node.hidden = i !== index; });
    Array.from(progress.children).forEach((node, i) => {
      if (i === index) node.setAttribute('aria-current', 'step');
      else node.removeAttribute('aria-current');
    });
    if (index === 1) { refreshComparison(); updateTripContext(); }
    $('step-' + index).focus();
  }
  // Only public municipality/program identifiers are read from the URL.
  // Personal plan fields never enter requests, URLs or storage.
  const legs = ['out', 'back'];
  const readiness = {unknown: 'まだ分からない', applying: '申請を考えている・申請中', held: 'パス・券などの利用準備ができている'};
  let indexData = null, prefectureData = null, cityData = null, selected = new Map(), requestId = 0;
  let supportProblem = '', loadingSupports = false;
  const params = new URLSearchParams(location.search);
  const node = (tag, text, className) => {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (className) el.className = className;
    return el;
  };
  const purposeHints = {
    '通院': '診察が長引いても帰れるか。帰りの別の便や、タクシーの呼び方も確認しましょう。',
    '買い物': '荷物を持って帰れるか。帰りだけバスやタクシーにする方法も考えられます。',
    '趣味・人に会う': '帰りたい時間に便があるか。最終便や、遅くなったときの帰り方を確認しましょう。',
    'その他': '用事が終わる時間に帰れるか。乗り場まで歩く道も含めて考えましょう。'
  };
  function purposeHint() {
    const purpose = document.querySelector('input[name="purpose"]:checked');
    return purposeHints[purpose?.value] || '行きと帰りは違う交通でも大丈夫。分からないところは空欄にして、調べることとして残せます。';
  }
  function updateTripContext() {
    $('trip-context').textContent = '家 → ' + (value('place') || '行きたい場所') + ' → 家';
    $('trip-hint').textContent = purposeHint();
  }
  document.querySelectorAll('input[name="purpose"]').forEach(input => input.addEventListener('change', () => {
    $('purpose-hint').textContent = purposeHint();
  }));
  function option(value, text) { const el = node('option', text); el.value = value; return el; }
  function safeLink(url, label) {
    const link = node('a', label);
    try {
      const parsed = new URL(url, location.href);
      if (!['https:', 'http:'].includes(parsed.protocol)) return node('span', label);
      link.href = parsed.href; link.target = '_blank'; link.rel = 'noopener';
    } catch (_) { return node('span', label); }
    return link;
  }
  function sourcesFor(program, container) {
    const sources = node('ul', undefined, 'outing-sources');
    for (const source of program.sources) {
      const item = node('li'); item.append(safeLink(source.url, source.label + ' ↗'));
      if (source.checked || source.updated) item.append(node('small', [source.updated && '更新：' + source.updated, source.checked && '確認：' + source.checked].filter(Boolean).join(' ／ ')));
      const urlText = node('span', source.url, 'outing-print-url'); item.append(urlText);
      sources.append(item);
    }
    container.append(sources, node('p', '掲載データの確認日：' + (program.checked || '記載なし'), 'outing-note'));
  }
  function programForLeg(key) { return selected.get(value(key + '-support')); }
  function distinctSupports() { return new Set(legs.map(key => value(key + '-support')).filter(Boolean)).size > 1; }
  function legConfirmed(key) {
    const choice = programForLeg(key);
    return !choice || (choice.ready === 'held' && $(key + '-confirmed').checked && cost(key) !== null && mode(key) !== '未定');
  }
  function updateLegs(resetCombination = false) {
    for (const [key, label] of [['out', '行き'], ['back', '帰り']]) {
      const choice = programForLeg(key);
      $(key + '-support-field').hidden = !selected.size;
      $(key + '-support-help').hidden = !selected.size;
      $(key + '-confirmed-wrap').hidden = !choice;
      $(key + '-normal-wrap').hidden = !choice;
      $(key + '-cost-label').textContent = label + (choice ? 'の自己負担額（円）' : 'の交通費（円）');
      $(key + '-support-help').textContent = choice
        ? readiness[choice.ready] + '。' + (choice.ready === 'held' ? '今回の路線・目的で使えるかも確認しましょう。' : '使えるようになった場合の仮の計画として残します。')
        : (selected.size ? '選んだ支援から、この片道で使うものを指定できます。' : '支援を使う場合は、この画面の「バス助成・タクシー支援も調べる」を開いてください。');
    }
    $('combination').hidden = !distinctSupports();
    if (resetCombination || !distinctSupports()) $('combination-confirmed').checked = false;
    if (resetCombination) resetMonthly();
    refreshComparison();
  }
  function clearLeg(key) {
    $(key + '-cost').value = '';
    $(key + '-normal-cost').value = '';
    resetMonthly();
    $(key + '-confirmed').checked = false;
  }
  function refreshSupportOptions() {
    for (const key of legs) {
      const previous = value(key + '-support');
      $(key + '-support').replaceChildren(option('', '支援を指定しない'), ...Array.from(selected.values(), choice => option(choice.program.id, choice.program.name)));
      if (selected.has(previous)) $(key + '-support').value = previous;
      else if (previous) clearLeg(key);
    }
    updateLegs(true);
  }
  function clearRegion() {
    cityData = null; selected.clear();
    refreshSupportOptions();
    $('support-area').hidden = true; $('support-list').replaceChildren();
    $('city-link').removeAttribute('href');
  }
  function renderPrograms(preselected) {
    $('support-list').replaceChildren();
    $('support-area').hidden = !cityData;
    if (!cityData) return;
    $('city-link').href = cityData.page;
    for (const program of cityData.programs) {
      const card = node('article', undefined, 'outing-support-card');
      const badge = node('p', (program.type === 'bus' ? 'バス関連' : 'タクシー関連') + ' · ' + program.status, 'outing-support-badge');
      card.append(badge);
      const heading = node('h5');
      let checkbox;
      if (program.selectable) {
        const label = node('label', undefined, 'outing-check-label');
        checkbox = document.createElement('input'); checkbox.type = 'checkbox'; checkbox.value = program.id;
        checkbox.checked = program.id === preselected;
        label.append(checkbox, node('span', program.name)); heading.append(label);
      } else heading.textContent = program.name;
      card.append(heading);
      const details = node('details'); details.append(node('summary', '対象・使い方・公式案内'));
      const dl = node('dl');
      for (const field of program.details) dl.append(node('dt', field.label), node('dd', field.text));
      details.append(dl); sourcesFor(program, details); card.append(details);
      if (!program.selectable) {
        card.append(node('p', '終了・未確認などの記録のため、計画への選択はできません。詳しい条件は地域のページで確認できます。', 'outing-note'));
      } else {
        const readyLabel = node('label', undefined, 'outing-field outing-ready');
        readyLabel.append(node('span', 'この支援の準備は？'));
        const ready = document.createElement('select');
        ready.setAttribute('aria-label', program.name + 'の準備');
        for (const [key, label] of Object.entries(readiness)) ready.append(option(key, label));
        readyLabel.append(ready); readyLabel.hidden = !checkbox.checked; card.append(readyLabel);
        if (checkbox.checked) selected.set(program.id, {program, ready: 'unknown'});
        checkbox.addEventListener('change', () => {
          if (checkbox.checked) selected.set(program.id, {program, ready: ready.value});
          else { selected.delete(program.id); ready.value = 'unknown'; }
          readyLabel.hidden = !checkbox.checked;
          refreshSupportOptions();
        });
        ready.addEventListener('change', () => {
          selected.get(program.id).ready = ready.value;
          for (const key of legs) if (value(key + '-support') === program.id) $(key + '-confirmed').checked = false;
          updateLegs(true);
        });
      }
      $('support-list').append(card);
    }
    if (cityData.supplements?.length) {
      const extra = node('details', undefined, 'outing-support-card');
      extra.append(node('summary', 'この地域の補足・追加の条件'));
      for (const item of cityData.supplements) {
        extra.append(node('strong', item.label), node('p', item.text));
        if (item.source) extra.append(safeLink(item.source, '補足の公式案内 ↗'));
        extra.append(node('p', item.checked ? '確認日：' + item.checked : '確認日の記載なし', 'outing-note'));
      }
      $('support-list').append(extra);
    }
    refreshSupportOptions();
  }
  const kanaRows = {'あ': 'あいうえおぁぃぅぇぉ', 'か': 'かきくけこ', 'さ': 'さしすせそ', 'た': 'たちつてとっ', 'な': 'なにぬねの', 'は': 'はひふへほ', 'ま': 'まみむめも', 'や': 'やゆよゃゅょ', 'ら': 'らりるれろ', 'わ': 'わをんゎ'};
  let cityGroup = '', cityOffset = 0, browsedRegion = '';
  function normalizePlace(text) {
    return (text || '').normalize('NFKC').toLowerCase().replace(/[ァ-ヶ]/g, char => String.fromCharCode(char.charCodeAt(0) - 96)).replace(/[\s　]/g, '');
  }
  function cityMatches(city, query) {
    const q = normalizePlace(query);
    return [city.name, city.kana].some(text => normalizePlace(text).includes(q));
  }
  function cityInitial(city) {
    const first = normalizePlace(city.kana || city.name).normalize('NFD').replace(/[\u3099\u309a]/g, '').charAt(0);
    return Object.keys(kanaRows).find(row => kanaRows[row].includes(first)) || 'その他';
  }
  function choiceButton(label, onClick, pressed = false) {
    const button = node('button', label); button.type = 'button';
    button.setAttribute('aria-pressed', String(pressed));
    button.addEventListener('click', onClick); return button;
  }
  function updatePickerSummary() {
    const pref = indexData?.prefectures.find(item => item.id === value('pref'));
    $('picker-summary').textContent = cityData ? '選択中：' + pref.name + ' ' + cityData.name : pref ? pref.name + 'の市町村を選んでください' : '地域はまだ選んでいません';
    $('picker-toggle').hidden = !cityData;
    $('picker-clear').hidden = !pref;
    $('inherited-region').hidden = !cityData;
    $('inherited-region').textContent = cityData ? cityData.name + 'の地域情報は、次の「往復・費用」で確認できます。' : '';
  }
  function renderPrefChoices(region) {
    browsedRegion = region;
    const prefs = indexData?.prefectures || [];
    const regions = [...new Set(prefs.map(pref => pref.region || 'その他'))];
    $('region-options').replaceChildren(...regions.map(label => choiceButton(label, () => { renderPrefChoices(label); $('pref-options').firstElementChild?.focus(); }, label === region)));
    $('pref-options').replaceChildren(...prefs.filter(pref => (pref.region || 'その他') === region).map(pref => choiceButton(pref.name, () => {
      if (value('pref') === pref.id && prefectureData) { $('city-search').focus(); return; }
      $('pref').value = pref.id; renderPrefChoices(region); setPref(pref.id, '', '', true);
    }, value('pref') === pref.id)));
  }
  function renderCityChoices(reset = true) {
    if (reset) cityOffset = 0;
    const cities = prefectureData?.cities || [];
    const query = value('city-search');
    const matches = cities.filter(city => cityMatches(city, query) && (!cityGroup || cityInitial(city) === cityGroup));
    if (cityOffset >= matches.length) cityOffset = 0;
    const rows = ['', ...Object.keys(kanaRows), ...(cities.some(city => cityInitial(city) === 'その他') ? ['その他'] : [])];
    $('city-initials').replaceChildren(...rows.map(row => choiceButton(row ? row === 'その他' ? row : row + '行' : 'すべて', () => {
      cityGroup = row; renderCityChoices();
      $('city-count').focus();
    }, cityGroup === row)));
    $('city-results').replaceChildren(...matches.slice(cityOffset, cityOffset + 12).map(city => {
      const button = choiceButton(city.name, () => {
        setCity(city.id); $('picker-summary').focus();
      }, city.id === value('city'));
      if (city.kana) button.append(node('small', city.kana));
      return button;
    }));
    $('city-count').textContent = matches.length ? matches.length + '件中 ' + (cityOffset + 1) + '〜' + Math.min(cityOffset + 12, matches.length) + '件' : '見つかりませんでした。文字を短くするか、絞り込みを解除してください。';
    $('city-prev').hidden = cityOffset === 0;
    $('city-more').hidden = cityOffset + 12 >= matches.length;
    $('city-reset').hidden = !query && !cityGroup;
  }
  function showCityPicker(show) {
    $('city-picker').hidden = !show;
    $('city-search').disabled = !show;
    if (!show) { $('city-search').value = ''; cityGroup = ''; cityOffset = 0; }
  }
  $('city-search').addEventListener('input', () => { cityGroup = ''; renderCityChoices(); });
  $('city-more').addEventListener('click', () => { cityOffset += 12; renderCityChoices(false); $('city-count').focus(); });
  $('city-prev').addEventListener('click', () => { cityOffset = Math.max(0, cityOffset - 12); renderCityChoices(false); $('city-count').focus(); });
  $('city-reset').addEventListener('click', () => { $('city-search').value = ''; cityGroup = ''; renderCityChoices(); $('city-search').focus(); });
  $('picker-toggle').addEventListener('click', () => {
    const open = $('picker-body').hidden;
    $('picker-body').hidden = !open; $('picker-toggle').setAttribute('aria-expanded', String(open));
    if (open) {
      renderPrefChoices(indexData?.prefectures.find(pref => pref.id === value('pref'))?.region || browsedRegion);
      renderCityChoices(); $('city-search').focus();
    }
  });
  $('picker-clear').addEventListener('click', () => {
    $('pref').value = ''; setPref('');
    $('picker-body').hidden = false; $('picker-toggle').setAttribute('aria-expanded', 'true');
    renderPrefChoices(browsedRegion); $('picker-summary').focus();
  });

  function setCity(id, supportId) {
    if (cityData?.id === id && !supportId) {
      $('picker-body').hidden = true; $('picker-toggle').setAttribute('aria-expanded', 'false'); return;
    }
    clearRegion(); supportProblem = '';
    cityData = prefectureData?.cities.find(city => city.id === id) || null;
    $('city').value = cityData ? id : '';
    updatePickerSummary();
    if (cityData) { $('picker-body').hidden = true; $('picker-toggle').setAttribute('aria-expanded', 'false'); }
    if (!cityData && id) supportProblem = '引き継ぐ市町村・支援を選び直す';
    if (!cityData) { $('support-status').textContent = id ? '指定された市町村が見つかりません。選び直してください。' : ''; return; }
    const valid = cityData.programs.find(program => program.id === supportId && program.selectable);
    renderPrograms(valid?.id);
    const count = cityData.programs.filter(program => program.selectable).length;
    $('support-status').textContent = supportId && !valid
      ? '指定された支援は引き継げませんでした。地域の条件を確認し、選び直してください。'
      : valid ? '地域のページから支援を引き継ぎました。準備状況を選んでください。'
      : count ? '検討する支援を選ぶと、行き・帰りに指定できます。'
      : 'この地域には、ここで選べる支援の記録がありません。制度がないことを示すものではありません。';
    if (supportId && !valid) supportProblem = '引き継げなかった支援を地域の公式案内で確認する';
  }
  async function fetchJSON(path) {
    const response = await fetch(path, {credentials: 'omit', referrerPolicy: 'no-referrer'});
    if (!response.ok) throw new Error('catalog unavailable');
    return response.json();
  }
  async function setPref(id, cityId, supportId, focusCity = false) {
    const token = ++requestId;
    clearRegion(); prefectureData = null; supportProblem = '';
    showCityPicker(false); updatePickerSummary();
    $('city').disabled = true;
    $('city').replaceChildren(option('', id ? '読み込み中…' : '都道府県を選んでください'));
    $('support-retry').hidden = true;
    if (!indexData?.prefectures.some(pref => pref.id === id)) { loadingSupports = false; $('support-status').textContent = ''; return; }
    loadingSupports = true; $('support-status').textContent = '地域の支援情報を読み込んでいます。';
    try {
      const data = await fetchJSON('assets/outing-supports/' + encodeURIComponent(id) + '.json?v=20261009-picker');
      if (token !== requestId) return;
      if (!Array.isArray(data.cities)) throw new Error('invalid catalog');
      prefectureData = data; loadingSupports = false;
      $('city').replaceChildren(option('', '市町村を選ぶ'), ...data.cities.map(city => option(city.id, city.name)));
      $('city').disabled = false; showCityPicker(true);
      $('city-picker-title').textContent = (indexData.prefectures.find(pref => pref.id === id)?.name || '') + 'の市町村を選ぶ';
      setCity(cityId || '', supportId); renderCityChoices();
      if (focusCity) $('city-search').focus();
    } catch (_) {
      if (token !== requestId) return;
      loadingSupports = false;
      supportProblem = '地域の支援情報を読み込めていないため、公式案内で確認する';
      $('support-status').textContent = '支援情報を読み込めませんでした。再読込するか、支援を指定せず計画を続けられます。';
      $('city').replaceChildren(option('', '読み込めませんでした'));
      $('support-retry').hidden = false;
    }
  }
  async function initSupports() {
    $('support-retry').hidden = true; loadingSupports = true;
    try {
      indexData = await fetchJSON('assets/outing-supports/index.json?v=20261009-picker');
      if (!Array.isArray(indexData.prefectures)) throw new Error('invalid catalog');
      $('pref').replaceChildren(option('', '都道府県を選ぶ'), ...indexData.prefectures.map(pref => option(pref.id, pref.name)));
      $('pref').disabled = false; loadingSupports = false;
      renderPrefChoices('');
      const pref = params.get('pref');
      if (pref && indexData.prefectures.some(item => item.id === pref)) {
        $('pref').value = pref; renderPrefChoices(indexData.prefectures.find(item => item.id === pref).region || 'その他');
        await setPref(pref, params.get('city'), params.get('support'));
        $('local-disclosure').open = true;
      } else if (pref || params.has('city') || params.has('support')) {
        supportProblem = '引き継ぐ地域・支援を選び直す';
        $('support-status').textContent = '指定された地域を引き継げませんでした。都道府県から選んでください。';
      }
    } catch (_) {
      loadingSupports = false; supportProblem = '地域の支援情報を読み込めていないため、公式案内で確認する';
      $('pref').replaceChildren(option('', '読み込めませんでした'));
      $('support-status').textContent = '地域情報を読み込めませんでした。支援を指定せず計画を続けられます。';
      $('support-retry').hidden = false;
    }
  }
  $('pref').addEventListener('change', () => setPref(value('pref')));
  $('city').addEventListener('change', () => setCity(value('city')));
  $('support-retry').addEventListener('click', () => indexData ? setPref(value('pref'), params.get('city'), params.get('support')) : initSupports());
  for (const key of legs) {
    $(key + '-support').addEventListener('change', () => { clearLeg(key); updateLegs(true); });
    $(key + '-mode').addEventListener('change', () => { clearLeg(key); updateLegs(true); });
    $(key + '-normal-cost').addEventListener('input', resetMonthly);
    for (const field of ['cost', 'time']) $(key + '-' + field).addEventListener('input', () => { $(key + '-confirmed').checked = false; resetMonthly(); });
  }
  $('monthly-trips').addEventListener('input', resetMonthly);
  $('combination-confirmed').addEventListener('change', resetMonthly);
  function invalidateTrip() {
    resetMonthly();
    for (const key of legs) $(key + '-confirmed').checked = false;
    $('combination-confirmed').checked = false;
  }
  for (const field of ['place', 'day']) $(field).addEventListener('input', invalidateTrip);
  document.querySelectorAll('input[name="purpose"]').forEach(input => input.addEventListener('change', invalidateTrip));
  initSupports();

  function normalCost(key) {
    return programForLeg(key) ? amount(key + '-normal-cost') : cost(key);
  }
  function comparison() {
    const enabled = legs.some(key => !!programForLeg(key));
    const provisional = legs.some(key => !legConfirmed(key));
    const count = amount('monthly-trips', 100, 1);
    const sum = values => values.every(n => n !== null) ? values.reduce((a, b) => a + b, 0) : null;
    const normal = sum(legs.map(normalCost));
    const blocked = distinctSupports() && !$('combination-confirmed').checked;
    const planned = blocked ? null : sum(legs.map(cost));
    const monthlyPending = enabled && !$('monthly-confirmed').checked;
    const monthlyNormal = count !== null && normal !== null ? count * normal : null;
    const monthlyPlanned = count !== null && planned !== null && !monthlyPending ? count * planned : null;
    const difference = enabled && normal !== null && planned !== null ? normal - planned : null;
    const monthlyDifference = enabled && monthlyNormal !== null && monthlyPlanned !== null ? monthlyNormal - monthlyPlanned : null;
    return {enabled, provisional, count, normal, planned, monthlyNormal, monthlyPlanned, difference, monthlyDifference, blocked, monthlyPending};
  }
  function differenceText(number) {
    return number === null ? '未確認' : number === 0 ? '差額なし' : yen(Math.abs(number)) + (number > 0 ? '少ない' : '多い');
  }
  function comparisonFields(c) {
    const monthlyMissing = c.count === null ? '回数が未入力・無効' : c.blocked ? '併用条件が未確認' : c.monthlyPending ? '券の残数・利用上限等が未確認' : '費用が未確認';
    return [
      ['計画の状態', c.provisional || c.blocked ? '申請・条件確認後の仮の計画' : '利用準備を確認した計画（本人の入力）'],
      ['通常の往復費用（1人）', c.normal === null ? '未確認' : yen(c.normal)],
      ['支援利用後の往復費用（1人）', c.blocked ? '併用条件が未確認のため合計しません' : c.planned === null ? '未確認' : yen(c.planned)],
      ['1回の往復の差額', differenceText(c.difference)],
      ['月の往復回数', c.count === null ? '未確認' : c.count + '回'],
      ['通常の月額', c.monthlyNormal === null ? '未確認' : yen(c.monthlyNormal)],
      ['支援利用後の月額', c.monthlyPlanned === null ? monthlyMissing : yen(c.monthlyPlanned)],
      ['月の差額', differenceText(c.monthlyDifference)],
      ['試算の範囲', '同じ往復を同じ料金で繰り返す交通費のみ。パスの購入・更新費や申請費などは含みません。実際の支給額や利用資格を保証するものではありません。']
    ];
  }
  function renderComparison(target, c, isResult = false) {
    target.replaceChildren(); target.hidden = !c.enabled && c.count === null;
    if (!c.enabled) {
      if (c.count !== null) {
        target.append(node('h3', 'この往復を続けた場合の交通費'));
        target.append(node('p', '月' + c.count + '回：' + (c.monthlyPlanned === null ? '未確認（片道の費用が空欄です）' : yen(c.monthlyPlanned)), 'outing-compare-difference'));
        target.append(node('p', '入力した1人分の往復交通費 × 月の回数。同じ交通・料金で出かける想定です。', 'outing-note'));
      }
      return;
    }
    target.append(node('p', c.provisional || c.blocked ? '申請・条件確認後の仮の計画' : '利用準備を確認した計画（本人の入力）', 'outing-comparison-state'), node('h3', '同じお出かけ、費用はどう変わる？'));
    const grid = node('div', undefined, 'outing-compare-grid');
    for (const [label, round, month, planned] of [['支援を使わない場合', c.normal, c.monthlyNormal, false], ['支援を使う場合', c.planned, c.monthlyPlanned, true]]) {
      const card = node('section', undefined, 'outing-compare-card');
      card.append(node('h4', label), node('p', '1人・1回の往復', 'outing-note'), node('p', round === null ? '未確認' : yen(round), 'outing-compare-amount'));
      if (planned && c.blocked) card.append(node('p', '併用条件が未確認のため合計しません', 'outing-note'));
      card.append(node('p', c.count === null ? '月の目安' : '月' + c.count + '回の目安', 'outing-note'));
      card.append(node('p', month === null ? '未確認' : yen(month), 'outing-compare-month'));
      grid.append(card);
    }
    target.append(grid);
    if (c.difference !== null) target.append(node('p', '1回の往復：' + differenceText(c.difference) + (c.monthlyDifference !== null ? ' ／ 月：' + differenceText(c.monthlyDifference) : ''), 'outing-compare-difference'));
    if (c.monthlyPending && c.count !== null) target.append(node('p', '支援利用後の月額は、券の残数・利用上限・有効期限を確認すると表示します。', 'outing-note'));
    target.append(node('p', '入力した交通費だけの比較です。パスの購入・更新費や申請費などは含みません。', 'outing-note'));
  }
  function resetMonthly() { $('monthly-confirmed').checked = false; }
  function refreshComparison() {
    const c = comparison();
    $('normal-help').hidden = !c.enabled;
    $('monthly-confirmed-wrap').hidden = !c.enabled;
    $('monthly-limit-help').hidden = !c.enabled;
    renderComparison($('comparison-preview'), c);
  }

  function collect() {
    const purpose = document.querySelector('input[name="purpose"]:checked');
    const comparisonData = comparison();
    const outCost = cost('out'), backCost = cost('back');
    const combinationPending = distinctSupports() && !$('combination-confirmed').checked;
    const provisional = legs.some(key => !legConfirmed(key));
    const total = combinationPending ? '併用条件が未確認のため合計しません'
      : outCost !== null && backCost !== null ? yen(outCost + backCost) : '未確認（未入力の費用があります）';
    const groups = legs.map((key, index) => {
      const choice = programForLeg(key);
      const fields = [['交通', mode(key)], ['時間・乗り場', shown(key + '-time')],
        ['使う支援', choice ? choice.program.name : '指定なし'],
        [choice ? (legConfirmed(key) ? '入力した自己負担額' : '仮の自己負担額') : '片道の交通費', costText(key)]];
      if (choice) fields.push(['支援を使わない場合の片道費用', normalCost(key) === null ? '未確認' : yen(normalCost(key))]);
      if (choice) fields.push(['支援利用の確認', legConfirmed(key) ? '準備・片道の条件と費用を本人が確認済み' : '申請・今回の利用条件などを確認してから使う計画']);
      return [index === 0 ? '行き' : '帰り', fields];
    });
    const preparation = [[provisional ? '申請・条件確認後の仮の往復費用（1人）' : '入力した往復の交通費（1人）', total], ['行きと帰りの予約・送迎のお願い', value('booking')], ['雨の日・間に合わないとき', shown('backup')], ['持ち物・気になること', shown('note')]];
    if (distinctSupports()) preparation.splice(1, 0, ['支援の併用条件', combinationPending ? '未確認' : '窓口で確認済み（本人の入力）']);
    groups.push(['費用と準備', preparation]);
    const checks = [];
    if (!value('place')) checks.push('行き先を決める');
    for (const [key, label] of [['out', '行き'], ['back', '帰り']]) {
      if (mode(key) === '未定') checks.push(label + 'の交通を決める');
      if (!value(key + '-time')) checks.push(label + 'の時間・乗り場を調べる');
      if (cost(key) === null) checks.push(label + 'の交通費を確認する');
      if (programForLeg(key) && !legConfirmed(key)) checks.push(label + 'で支援を使える路線・目的・自己負担額を確認する');
    }
    if (combinationPending) checks.push('行きと帰りに指定した2つの制度を併用できるか窓口で確認する。片道ずつでも併用できない場合があります');
    for (const {program, ready} of selected.values()) {
      if (ready !== 'held') checks.push(program.name + '：対象条件と申請・交付の準備を確認する');
      else checks.push(program.name + '：必要なパス・券などの持ち物と有効期限・残数を確認する');
    }
    if (comparisonData.enabled) {
      if (comparisonData.normal === null) checks.push('比較する通常の交通費を、同じ交通・区間・条件で確認する');
      if (comparisonData.count !== null && comparisonData.monthlyPending) checks.push('月の回数すべてで使える券の残数・利用上限・有効期限を確認する');
    }
    if (supportProblem) checks.push(supportProblem);
    if (loadingSupports) checks.push('地域の支援情報が読み込み中のため、読み込み後に支援を選び直す');
    if ($('booking').selectedIndex === 0 || $('booking').selectedIndex === 2) checks.push('行きと帰りの予約・送迎のお願いを確認する');
    if (!value('backup')) checks.push('雨の日・予定が変わったときの代案を考える');
    if (!value('day')) checks.push('日程が決まったら、その曜日・時間の便が使えるか確認する');
    checks.push('出発前に運行日・時刻・運賃をもう一度確かめる');
    const prefName = indexData?.prefectures.find(pref => pref.id === value('pref'))?.name;
    return {purpose: purpose ? purpose.value : '未定', place: shown('place'), day: value('day') || '日程はこれから相談', region: cityData ? prefName + ' ' + cityData.name : '指定なし', groups, checks, comparison: comparisonData};
  }
  function render() {
    const plan = collect();
    $('result-destination').textContent = [plan.region !== '指定なし' ? 'お住まい：' + plan.region : '', plan.purpose !== '未定' ? plan.purpose : '', plan.place, plan.day].filter(Boolean).join(' ／ ');
    $('result-route').textContent = '家 → ' + (value('place') || '行き先はこれから相談') + ' → 家';
    $('result-next').textContent = plan.checks[0];
    const overview = [
      ['往復の方法', legs.every(key => mode(key) !== '未定') ? mode('out') + 'で行き、' + mode('back') + 'で帰る案' : 'まだ決めていない交通があります'],
      ['1人の往復費用', plan.groups[2][1][0][1] + (plan.comparison.provisional && plan.comparison.planned !== null ? '（仮の費用）' : '')],
      ['予約・送迎', value('booking') || 'まだ未確認']
    ];
    $('result-overview').replaceChildren(...overview.map(([label, text]) => {
      const card = node('section'); card.append(node('h3', label), node('p', text)); return card;
    }));
    renderComparison($('result-comparison'), plan.comparison, true);
    const container = $('result-details');
    container.replaceChildren();
    for (const [title, fields] of plan.groups) {
      const section = document.createElement('section');
      const heading = document.createElement('h3');
      heading.textContent = title;
      section.append(heading);
      const dl = document.createElement('dl');
      for (const [label, text] of fields) {
        const dt = document.createElement('dt'), dd = document.createElement('dd');
        dt.textContent = label; dd.textContent = text;
        dl.append(dt, dd);
      }
      section.append(dl); container.append(section);
    }
    $('result-checks').replaceChildren(...plan.checks.map(text => {
      const li = document.createElement('li'); li.textContent = text; return li;
    }));
    const supportResult = $('result-supports');
    supportResult.replaceChildren(); supportResult.hidden = !selected.size;
    if (selected.size) supportResult.append(node('h3', '検討する支援と準備'));
    for (const {program, ready} of selected.values()) {
      const section = node('section');
      section.append(node('h4', program.name), node('p', readiness[ready]));
      const conditions = node('details', undefined, 'outing-retained-conditions');
      conditions.append(node('summary', '利用条件を見返す'));
      const dl = node('dl');
      for (const field of program.details) dl.append(node('dt', field.label), node('dd', field.text));
      conditions.append(dl); section.append(conditions);
      sourcesFor(program, section);
      supportResult.append(section);
    }
    if (selected.size && cityData?.supplements?.length) {
      const extra = node('details', undefined, 'outing-retained-conditions'); extra.append(node('summary', '地域の補足・追加の条件'));
      for (const item of cityData.supplements) {
        extra.append(node('strong', item.label), node('p', item.text));
        if (item.source) { extra.append(safeLink(item.source, '補足の公式案内 ↗'), node('span', item.source, 'outing-print-url')); }
        if (item.checked) extra.append(node('p', '確認日：' + item.checked, 'outing-note'));
      }
      supportResult.append(extra);
    }
    const lines = ['車なしで通うための検討メモ', 'まず確認すること：' + plan.checks[0], '本人の地域：' + plan.region, '目的：' + plan.purpose, '行き先：' + plan.place, '利用する日・時間の目安：' + plan.day];
    for (const [title, fields] of plan.groups) {
      lines.push('', '【' + title + '】', ...fields.map(([label, text]) => label + '：' + text));
    }
    if (plan.comparison.enabled) lines.push('', '【交通費の比較】', ...comparisonFields(plan.comparison).map(([label, text]) => label + '：' + text));
    else if (plan.comparison.count !== null) lines.push('', '【続けた場合の交通費】', '月' + plan.comparison.count + '回：' + (plan.comparison.monthlyPlanned === null ? '未確認' : yen(plan.comparison.monthlyPlanned)), '入力した1人分の往復交通費 × 月の回数。同じ交通・料金で出かける想定です。');
    if (selected.size) {
      lines.push('', '【検討する支援と準備】');
      for (const {program, ready} of selected.values()) {
        lines.push(program.name + '：' + readiness[ready], '掲載データ確認日：' + (program.checked || '記載なし'), ...program.details.map(field => field.label + '：' + field.text), ...program.sources.map(source => source.label + '：' + source.url + (source.checked ? '（確認日：' + source.checked + '）' : '')));
      }
    }
    if (selected.size && cityData?.supplements?.length) {
      lines.push('', '【地域の補足・追加の条件】');
      for (const item of cityData.supplements) lines.push(item.label + '：' + item.text, item.source, '確認日：' + (item.checked || '記載なし'));
    }
    lines.push('', '【調べること・出発前に確かめること】', ...plan.checks.map(text => '・' + text), '', '入力内容をまとめたメモです。運行・予約・運賃は利用前に公式案内で確認してください。', 'じもとくらべ https://jimotokurabe.jp/outing-plan.html');
    $('memo').value = lines.join('\n');
    $('status').textContent = '';
  }
  function finish() {
    if (!validateCosts()) return;
    render();
    $('form').hidden = true; progress.hidden = true;
    $('result').hidden = false;
    $('result-title').focus();
  }
  $('form').addEventListener('submit', event => { event.preventDefault(); });
  document.querySelectorAll('[data-next]').forEach(button => button.addEventListener('click', () => {
    if (step === 1 && !validateCosts()) return;
    showStep(Math.min(2, step + 1));
  }));
  document.querySelectorAll('[data-back]').forEach(button => button.addEventListener('click', () => showStep(Math.max(0, step - 1))));
  $('finish').addEventListener('click', finish);
  $('edit').addEventListener('click', () => showStep(0));
  $('copy').addEventListener('click', async () => {
    try {
      if (!navigator.clipboard) throw new Error('clipboard unavailable');
      await navigator.clipboard.writeText($('memo').value);
      $('status').textContent = '検討メモをコピーしました。家族との相談や、交通・支援の窓口への確認に使えます。';
    } catch (error) {
      document.querySelector('.outing-memo').open = true;
      $('memo').focus(); $('memo').select();
      $('status').textContent = 'コピー用の文章を選択しました。端末のコピー操作を使ってください。';
    }
  });
  $('print').addEventListener('click', () => window.print());
  // Keyboard/browser printing also includes the latest inputs, even midway.
  let printHidden = null;
  window.addEventListener('beforeprint', () => {
    printHidden = $('result').hidden;
    render();
    document.querySelectorAll('#outing-result .outing-retained-conditions').forEach(details => { details.open = true; });
    $('result').hidden = false;
  });
  window.addEventListener('afterprint', () => {
    if (printHidden !== null) $('result').hidden = printHidden;
    printHidden = null;
    document.querySelectorAll('#outing-result .outing-retained-conditions').forEach(details => { details.open = false; });
  });
  $('form').addEventListener('input', refreshComparison);
  $('form').addEventListener('change', refreshComparison);
  refreshComparison();
  app.hidden = false;
})();
