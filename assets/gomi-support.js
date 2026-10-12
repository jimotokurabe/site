(() => {
  'use strict';
  const fontButtons = document.querySelectorAll('[data-size]');
  const setFontSize = (size, save = false) => {
    document.documentElement.classList.toggle('large', size === 'large');
    fontButtons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.size === size)));
    if (save) { try { sessionStorage.setItem('jk-national-size', size); } catch (_) {} }
  };
  try { setFontSize(sessionStorage.getItem('jk-national-size') || 'normal'); } catch (_) { setFontSize('normal'); }
  fontButtons.forEach(button => button.addEventListener('click', () => setFontSize(button.dataset.size, true)));
  const hub = document.querySelector('[data-gomi-hub]');
  if (hub) {
    const search = hub.querySelector('[data-gomi-city-search]');
    const rows = [...hub.querySelectorAll('[data-city-search]')];
    const count = hub.querySelector('[data-gomi-city-count]');
    const empty = hub.querySelector('[data-gomi-no-results]');
    search?.addEventListener('input', () => {
      const normalize = (value) => value.normalize('NFKC').toLocaleLowerCase('ja')
        .replace(/[\u30A1-\u30F6]/g, (character) => String.fromCharCode(character.charCodeAt(0) - 0x60));
      const query = normalize(search.value.trim());
      let visible = 0;
      rows.forEach((row) => {
        const match = normalize(row.dataset.citySearch).includes(query);
        row.hidden = !match;
        if (match) visible += 1;
      });
      count.textContent = `${visible}地域を表示しています。`;
      empty.hidden = visible > 0;
    });
  }
  const revealFragment = () => {
    let target;
    try { target = document.getElementById(decodeURIComponent(location.hash.slice(1))); } catch (_) { return; }
    if (!target) return;
    for (let node = target.parentElement; node; node = node.parentElement) if (node.tagName === 'DETAILS') node.open = true;
  };
  window.addEventListener('hashchange', revealFragment);
  revealFragment();
  const root = document.querySelector('.gomi-city');
  if (!root) return;

  const routeSelect = root.querySelector('[data-gomi-route]');
  const jumpSelect = root.querySelector('[data-gomi-jump]');
  const locationSelect = root.querySelector('[data-gomi-location]');
  const preview = root.querySelector('[data-gomi-preview]');
  const status = root.querySelector('[data-gomi-status]');
  const itemInput = root.querySelector('[data-gomi-item]');
  const notesInput = root.querySelector('[data-gomi-notes]');
  let statusTimer;

  const text = (node) => (node?.textContent || '').replace(/\s+/g, ' ').trim();
  const selectedCard = () => root.querySelector(`#${CSS.escape(routeSelect.value)}`);
  const scrollToCard = (id, hash = false) => {
    const card = root.querySelector(`#${CSS.escape(id)}`);
    if (!card) return;
    card.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
    card.classList.add('gomi-relevant');
    window.setTimeout(() => card.classList.remove('gomi-relevant'), 3500);
    if (hash) history.replaceState(null, '', `#${encodeURIComponent(id)}`);
  };
  const sourceLine = (fact) => {
    const card = fact.closest('.gomi-route-card');
    const ids = (fact.dataset.sourceIds || '').split(/\s+/).filter(Boolean);
    const refs = ids.map((id) => {
      const source = card.querySelector(`[data-source-id="${CSS.escape(id)}"]`);
      const link = source?.querySelector('a[href^="http"]');
      if (!source || !link) return '';
      const dates = [];
      if (source.dataset.updated) dates.push(`公式更新 ${source.dataset.updated}`);
      if (source.dataset.checked) dates.push(`確認 ${source.dataset.checked}`);
      return `${text(source.querySelector('span'))}${dates.length ? `（${dates.join('・')}）` : ''}: ${link.href}`;
    }).filter(Boolean);
    return refs.length ? refs.join(' / ') : '出典URLは登録されていません';
  };
  const makeMemo = () => {
    const card = selectedCard();
    if (!card) return '';
    const lines = [
      `${text(root.querySelector('h1'))} 相談メモ`,
      `確認する経路：${text(card.querySelector('h3'))}（${text(card.querySelector('.gomi-route-type'))}）`,
      `ごみの種類・品目：${itemInput.value.trim() || '未入力'}`,
      `どこまで運べるか：${locationSelect.value}`,
      '',
      '制度の案内（条件・費用・制限を含む）',
    ];
    card.querySelectorAll('.gomi-fact').forEach((fact) => {
      const label = text(fact.querySelector('dt')).replace(text(fact.querySelector('.gomi-state-label')), '').trim();
      const valueNode = fact.querySelector('dd').cloneNode(true);
      valueNode.querySelector('.gomi-field-sources')?.remove();
      const value = fact.querySelector('[data-memo-value]')?.dataset.memoValue || text(valueNode);
      const refs = text(fact.querySelector('.gomi-field-sources'));
      const state = text(fact.querySelector('.gomi-state-label'));
      lines.push(`・${label}［${state}］：${value}（${refs}）`);
      fact.querySelectorAll('.gomi-contact-link').forEach(link => lines.push(`${text(link)}: ${link.href}`));
    });
    lines.push('', '出典と確認日');
    const allSources = new Set();
    card.querySelectorAll('.gomi-fact').forEach(fact => allSources.add(sourceLine(fact)));
    lines.push(...allSources);
    const date = text(card.querySelector('.gomi-review-date'));
    if (date) lines.push('', date);
    card.querySelectorAll('.gomi-not-found, .gomi-search-scope, .gomi-evidence').forEach(note => lines.push('', '調査状況：' + text(note)));
    const questions = [...card.querySelectorAll('.gomi-service-questions li')].map(text).filter(Boolean);
    lines.push('', 'この方法について問い合わせること', questions.length ? questions.map(question => '・' + question).join('\n') : '個別の確認事項は登録されていません。利用条件と受付状況は公式窓口で確認してください。');
    const commonQuestions = [...root.querySelectorAll('.gomi-common-questions li')].map(text).filter(Boolean);
    if (commonQuestions.length) lines.push('', '市内の各方法に共通する確認事項', ...commonQuestions.map(question => '・' + question));
    if (notesInput.value.trim()) lines.push('', '自分で追加した確認事項', notesInput.value.trim());
    lines.push('', 'このメモは利用決定・予約ではありません。掲載情報をもとにした相談用メモです。利用条件と受付状況は公式窓口で確認してください。');
    return lines.join('\n');
  };
  const updatePreview = () => {
    if (preview) preview.value = makeMemo();
    const printMemo = root.querySelector('[data-gomi-print-memo]');
    if (printMemo) printMemo.textContent = makeMemo();
  };
  const setStatus = (message) => {
    status.textContent = message;
    window.clearTimeout(statusTimer);
    statusTimer = window.setTimeout(() => { status.textContent = ''; }, 6000);
  };
  const go = (id, hash = false) => {
    if (!id) return;
    scrollToCard(id, hash);
  };

  routeSelect.addEventListener('change', () => { updatePreview(); });
  root.querySelectorAll('[data-gomi-memo-route]').forEach(link => link.addEventListener('click', () => {
    routeSelect.value = link.dataset.gomiMemoRoute;
    updatePreview();
  }));
  jumpSelect?.addEventListener('change', () => {
    if (jumpSelect.value) {
      routeSelect.value = jumpSelect.value;
      updatePreview();
      go(jumpSelect.value, true);
      jumpSelect.value = '';
    }
  });
  [itemInput, notesInput, locationSelect].forEach((input) => {
    input.addEventListener('input', updatePreview);
    input.addEventListener('change', updatePreview);
  });
  locationSelect.addEventListener('change', () => {
    // This is a reading aid only. It leaves every route and qualification fact visible.
    root.querySelectorAll('.gomi-route-card').forEach((card) => card.classList.remove('gomi-relevant'));
    const choice = locationSelect.value;
    const kinds = choice.includes('室内') ? ['bulky_carry_support']
      : choice.includes('施設') ? ['self_dropoff']
      : choice.includes('玄関') ? ['daily_support', 'bulky_carry_support']
      : choice.includes('屋外') ? ['regular_bulky'] : [];
    kinds.forEach((kind) => root.querySelectorAll(`.gomi-route-card[data-kind="${kind}"]`).forEach((card) => card.classList.add('gomi-relevant')));
    if (choice !== 'まだ分からない') {
      setStatus('選択に関係する案内を目立たせました。条件や他の方法もすべて下に表示しています。');
    }
  });
  root.querySelector('[data-gomi-copy]').addEventListener('click', async () => {
    const value = makeMemo();
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
        setStatus('相談メモをコピーしました。');
        return;
      }
    } catch (_) {
      // Continue to a user initiated manual-copy fallback.
    }
    const helper = document.createElement('textarea');
    helper.value = value;
    helper.setAttribute('aria-label', 'コピーする相談メモ');
    helper.style.position = 'fixed';
    helper.style.left = '-10000px';
    document.body.append(helper);
    helper.select();
    let copied = false;
    try { copied = document.execCommand('copy'); } catch (_) { copied = false; }
    helper.remove();
    if (copied) setStatus('相談メモをコピーしました。');
    else {
      preview.focus();
      preview.select();
      setStatus('自動コピーできませんでした。表示したメモを選択してコピーしてください。');
    }
  });
  root.querySelector('[data-gomi-print]').addEventListener('click', () => {
    document.body.classList.add('gomi-print-memo-only');
    updatePreview();
    window.print();
  });
  window.addEventListener('afterprint', () => document.body.classList.remove('gomi-print-memo-only'));
  window.addEventListener('beforeprint', () => {
    const printMemo = root.querySelector('[data-gomi-print-memo]');
    if (printMemo) printMemo.textContent = makeMemo();
  });
  updatePreview();
})();
