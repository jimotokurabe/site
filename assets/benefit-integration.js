(() => {
  'use strict';
  const panels = [...document.querySelectorAll('.integrated-panel')];
  const cards = [...document.querySelectorAll('[data-pick]')];
  const share = document.querySelector('#family [data-share-city]');
  if (panels.length !== 4 || cards.length !== 4 || !share) return;
  const canonical = document.querySelector('link[rel="canonical"]')?.href || location.href.split('#')[0];
  const storeKey = 'jimoto-benefit-selection:' + canonical;
  const valid = new Set(panels.map(panel => panel.id));
  let selected = [], storageAvailable = true;
  try {
    const stored = JSON.parse(localStorage.getItem(storeKey) || '[]');
    if (Array.isArray(stored)) selected = [...new Set(stored.filter(id => valid.has(id)))];
  } catch { storageAvailable = false; }
  const title = id => document.querySelector('#' + id + ' h2')?.textContent.trim() || id;
  function select(id, focus = false) {
    if (!valid.has(id)) return;
    panels.forEach(panel => panel.classList.toggle('is-selected', panel.id === id));
    cards.forEach(card => {
      if (card.dataset.pick === id) card.setAttribute('aria-current', 'true');
      else card.removeAttribute('aria-current');
    });
    if (focus) document.getElementById(id).focus({preventScroll:true});
  }
  function reveal(hash, focus = false) {
    let id;
    try { id = decodeURIComponent(hash.replace(/^#/, '')); } catch { return; }
    const target = document.getElementById(id);
    if (!target) return;
    const panel = target.closest('.integrated-panel');
    if (panel) select(panel.id, focus);
    else if (id === 'statewide' || id === 'sw-h') select('benefit', focus);
    let parent = target.parentElement;
    while (parent) { if (parent.tagName === 'DETAILS') parent.open = true; parent = parent.parentElement; }
  }
  select(cards[0].dataset.pick);
  document.body.classList.add('integrated-enhanced');
  reveal(location.hash);
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href^="#"]');
    if (link) reveal(link.getAttribute('href'), true);
  });
  window.addEventListener('hashchange', () => reveal(location.hash, true));
  const status = document.getElementById('selected-status');
  const list = document.getElementById('selected-list');
  // Keep the existing share control beside the selected items instead of
  // requiring another trip past the checklist. Its existing fallback remains.
  list.after(share);
  let timer;
  function toast(message) {
    const el = document.querySelector('.integration-toast');
    el.textContent = message; el.hidden = false;
    clearTimeout(timer); timer = setTimeout(() => { el.hidden = true; }, 3500);
  }
  function save() {
    try { localStorage.setItem(storeKey, JSON.stringify(selected)); storageAvailable = true; }
    catch { storageAvailable = false; }
  }
  function render() {
    list.replaceChildren();
    status.textContent = selected.length
      ? `${selected.length}項目を選択中。金額は合算しません。${storageAvailable ? '選択はこの端末に保存されます。' : 'このページを開いている間だけ保持します。'}`
      : 'まだ支援を選んでいません。下のボタンでは、このページのURLと主な出典をコピーできます。';
    share.textContent = selected.length ? `選んだ${selected.length}項目のメモを確認・コピー` : 'このページの案内を確認・コピー';
    document.querySelectorAll('[data-selected-summary]').forEach(link => {
      link.textContent = selected.length ? `追加済み${selected.length}項目をまとめて確認する →` : '複数の支援をまとめる・確認項目を見る →';
    });
    selected.forEach(id => {
      const row = document.createElement('div'), link = document.createElement('a'), button = document.createElement('button');
      row.className = 'selected-row'; link.href = '#' + id; link.textContent = title(id);
      button.type = 'button'; button.textContent = '解除'; button.setAttribute('aria-label', title(id) + 'をメモから解除');
      button.addEventListener('click', () => { selected = selected.filter(value => value !== id); save(); render(); share.focus(); });
      row.append(link, button); list.append(row);
    });
    document.querySelectorAll('[data-add-family]').forEach(button => {
      const chosen = selected.includes(button.dataset.addFamily);
      button.textContent = chosen ? '✓ 家族用メモに追加済み' : '＋ 家族用メモに追加';
      button.setAttribute('aria-pressed', String(chosen));
    });
  }
  document.querySelectorAll('[data-add-family]').forEach(button => button.addEventListener('click', () => {
    const id = button.dataset.addFamily;
    if (!valid.has(id)) return;
    if (selected.includes(id)) { selected = selected.filter(value => value !== id); toast('家族用メモから外しました。'); }
    else { selected.push(id); toast('家族用メモに追加しました。「追加済みの項目をまとめて確認」から見返せます。'); }
    save(); render();
  }));
  const dialog = document.getElementById('selection-dialog'), memo = document.getElementById('selection-text');
  const copyStatus = document.getElementById('selection-copy-status');
  let memoOpener = share;
  const closeMemo = document.createElement('button');
  closeMemo.type = 'button'; closeMemo.id = 'selection-close'; closeMemo.textContent = '閉じて戻る';
  document.getElementById('selection-copy').after(closeMemo);
  closeMemo.addEventListener('click', () => {
    if (typeof dialog.close === 'function') dialog.close();
    else { dialog.removeAttribute('open'); memoOpener.focus({preventScroll:true}); }
  });
  function openMemo(ids, opener, entryPoint) {
    memoOpener = opener;
    let text = `${document.querySelector('h1').textContent.trim()}\n${canonical}\n\n家族と確認する掲載記録です。利用前に公式案内・窓口で現在の条件を確認してください。\n複数項目に同じ制度が含まれる場合があります。金額は合算しません。\n`;
    const includedReferences = new Set();
    ids.forEach(id => {
      const record = document.querySelector('#' + id + ' .original-record');
      // Keep all conditions, dates, and source associations, including closed disclosures.
      const clone = record.cloneNode(true);
      // A grouped bus/taxi panel points to the municipal return record. Include
      // those conditions when sharing the panel alone, once per shared memo.
      const shared = record.querySelector('.cross a[href="#return-record"]')
        ? document.getElementById('return-record') : null;
      const alreadyIncluded = shared && ids.some(other =>
        document.querySelector('#' + other + ' .original-record')?.contains(shared));
      if (shared && !record.contains(shared) && !alreadyIncluded && !includedReferences.has(shared.id)) {
        const heading = document.createElement('h3');
        heading.textContent = '同じ支援の対象条件・申請先';
        clone.append(heading, shared.cloneNode(true));
        includedReferences.add(shared.id);
      }
      clone.querySelectorAll('svg,script,style').forEach(node => node.remove());
      clone.querySelectorAll('a[href]').forEach(link => {
        const url = new URL(link.getAttribute('href'), canonical);
        if (/^https?:$/.test(url.protocol)) link.append(document.createTextNode(' (' + url.href + ')'));
      });
      clone.querySelectorAll('br').forEach(node => node.replaceWith(document.createTextNode('\n')));
      clone.querySelectorAll('p,li,dt,dd,h2,h3,h4,summary,div,.badge,.sources span').forEach(node => node.append(document.createTextNode('\n')));
      text += '\n【' + title(id) + '】\n' + clone.textContent.replace(/[ \t]+/g, ' ').replace(/\n\s*\n/g, '\n').trim() + '\n';
    });
    document.getElementById('selection-title').textContent = entryPoint === 'support_panel' ? 'この支援の共有メモ' : `選んだ${ids.length}項目の共有メモ`;
    memo.value = text; copyStatus.textContent = '';
    if (typeof dialog.showModal === 'function') dialog.showModal(); else dialog.setAttribute('open', '');
    window.jkAnalytics?.familyMemoOpened?.(entryPoint);
  }
  document.querySelectorAll('[data-share-benefit]').forEach(button => button.addEventListener('click', () => {
    if (valid.has(button.dataset.shareBenefit)) openMemo([button.dataset.shareBenefit], button, 'support_panel');
  }));
  share.addEventListener('click', event => {
    if (!selected.length) return;
    event.preventDefault(); event.stopImmediatePropagation();
    openMemo(selected, share, 'family_section');
  }, true);
  dialog.addEventListener('close', () => memoOpener.focus({preventScroll:true}));
  document.getElementById('selection-copy').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(memo.value); window.jkAnalytics?.memoCopied('selected_supports'); copyStatus.textContent = 'コピーしました。連絡アプリなどに貼り付けられます。'; }
    catch { memo.focus(); memo.select(); copyStatus.textContent = '自動コピーできませんでした。選択した文章を手動でコピーしてください。'; }
  });
  render();
  // Count an entrance only when visible. The analytics module deduplicates by
  // entrance per page; text, selected IDs, and memo contents are never passed.
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting || entry.intersectionRatio < .25) return;
        const point = entry.target.matches('.family-actions') ? 'support_panel' : 'family_section';
        window.jkAnalytics?.familyMemoViewed?.(point);
        observer.unobserve(entry.target);
      });
    }, {threshold: .25});
    document.querySelectorAll('.family-actions, #selected-benefits').forEach(element => observer.observe(element));
  }
})();
