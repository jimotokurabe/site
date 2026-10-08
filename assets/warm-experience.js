(() => {
  'use strict';

  const phrases = [
    'これからのお出かけ、一緒に考えてみよう。',
    '通院や買い物、車以外ならどう行けるか一緒に調べてみよう。',
    '返納したら、どんな特典があるか一緒に見てみない？'
  ];

  function copyText(value) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(value).then(() => true).catch(() => legacyCopy(value));
    }
    return Promise.resolve(legacyCopy(value));
  }

  function legacyCopy(value) {
    const field = document.createElement('textarea');
    field.value = value;
    field.setAttribute('readonly', '');
    field.style.position = 'fixed';
    field.style.opacity = '0';
    document.body.append(field);
    field.select();
    let copied = false;
    try { copied = document.execCommand('copy'); } catch (error) { copied = false; }
    field.remove();
    return copied;
  }

  const familyDialog = document.getElementById('warm-family-dialog');
  if (familyDialog) {
    const output = familyDialog.querySelector('[data-family-phrase-output]');
    const status = familyDialog.querySelector('[data-family-copy-status]');
    let selectedPhrase = 0;
    document.querySelectorAll('[data-family-open]').forEach(button => button.addEventListener('click', () => {
      if (typeof familyDialog.showModal === 'function') familyDialog.showModal();
      else familyDialog.setAttribute('open', '');
    }));
    familyDialog.querySelectorAll('[data-family-phrase]').forEach(button => button.addEventListener('click', () => {
      selectedPhrase = Number(button.dataset.familyPhrase);
      if (!Number.isInteger(selectedPhrase) || !phrases[selectedPhrase]) selectedPhrase = 0;
      familyDialog.querySelectorAll('[data-family-phrase]').forEach(item => {
        item.setAttribute('aria-pressed', String(item === button));
      });
      if (output) output.textContent = phrases[selectedPhrase];
      if (status) status.textContent = '';
    }));
    familyDialog.querySelectorAll('[data-family-close]').forEach(button => button.addEventListener('click', () => familyDialog.close?.()));
    familyDialog.querySelectorAll('[data-family-copy]').forEach(button => button.addEventListener('click', async () => {
      const copied = await copyText(phrases[selectedPhrase]);
      if (status) status.textContent = copied ? 'ひと言をコピーしました。' : 'コピーできませんでした。ひと言を選択してコピーしてください。';
    }));
  }

  const checklist = [...document.querySelectorAll('#family .checklist input[type="checkbox"]')];
  const checkStatus = document.getElementById('check-status');
  if (checklist.length && checkStatus) {
    const pageKey = `jimoto-family-checks:${document.querySelector('link[rel="canonical"]')?.href || location.pathname}`;
    let storageAvailable = true;
    try {
      const saved = JSON.parse(localStorage.getItem(pageKey) || '[]');
      checklist.forEach((box, index) => { box.checked = saved[index] === true; });
    } catch (error) { storageAvailable = false; }

    const updateStatus = () => {
      const checked = checklist.filter(box => box.checked).length;
      checkStatus.textContent = `${checklist.length}項目のうち${checked}項目を確認。チェックはこの${storageAvailable ? '端末に保存されます' : 'ページを開いている間だけ保持されます'}。`;
    };
    updateStatus();
    checklist.forEach(box => box.addEventListener('change', () => {
      try {
        localStorage.setItem(pageKey, JSON.stringify(checklist.map(item => item.checked)));
        storageAvailable = true;
      } catch (error) { storageAvailable = false; }
      // The existing listener reports session-only state; update after it runs.
      window.setTimeout(updateStatus, 0);
    }));
  }

  let shareDialog;
  let shareStatus;
  let shareText;
  function ensureShareDialog() {
    if (shareDialog) return shareDialog;
    shareDialog = document.createElement('dialog');
    shareDialog.id = 'warm-share-dialog';
    shareDialog.setAttribute('aria-labelledby', 'warm-share-title');
    shareDialog.innerHTML = '<form method="dialog"><button type="submit" aria-label="閉じる">閉じる</button></form>' +
      '<h2 id="warm-share-title">この市町村の案内を共有</h2>' +
      '<p>公開ページと公式出典を含む案内文をコピーできます。</p>' +
      '<textarea readonly rows="12" data-share-text aria-label="共有する案内文"></textarea>' +
      '<p role="status" aria-live="polite" data-share-status></p>' +
      '<button type="button" data-share-copy>案内文をコピー</button>' +
      '<button type="button" data-share-close>閉じる</button>';
    document.body.append(shareDialog);
    shareStatus = shareDialog.querySelector('[data-share-status]');
    shareText = shareDialog.querySelector('[data-share-text]');
    shareDialog.querySelector('[data-share-close]').addEventListener('click', () => shareDialog.close?.());
    shareDialog.querySelector('[data-share-copy]').addEventListener('click', async () => {
      const copied = await copyText(shareText.value);
      shareStatus.textContent = copied ? '案内文をコピーしました。' : 'コピーできませんでした。案内文を選択してコピーしてください。';
    });
    return shareDialog;
  }

  function shareContents() {
    const canonical = document.querySelector('link[rel="canonical"]')?.href;
    const pageUrl = canonical || location.href;
    const internalHosts = new Set([location.hostname]);
    try { if (canonical) internalHosts.add(new URL(canonical, location.href).hostname); } catch (error) {}
    const title = document.title || document.querySelector('h1')?.textContent?.trim() || pageUrl;
    const sources = [];
    const sourceLinks = [...document.querySelectorAll('main .sources a[href]')];
    const allMainLinks = [...document.querySelectorAll('main a[href]')];
    const candidates = [...sourceLinks, ...allMainLinks];
    candidates.forEach(link => {
      const url = link.href;
      let parsed;
      try { parsed = new URL(url, location.href); } catch (error) { return; }
      if (!/^https?:$/.test(parsed.protocol) || internalHosts.has(parsed.hostname)) return;
      if (sources.some(source => source.url === url) || sources.length >= 5) return;
      const item = link.closest('li') || link.parentElement;
      const date = item?.textContent?.match(/(?:確認日|内容の確認日)\s*[:：]\s*([0-9]{4}[-年][0-9]{1,2}[-月][0-9]{1,2}日?)/)?.[1];
      sources.push({ label: link.textContent.trim().replace(/\s+/g, ' '), url, date });
    });
    return `${title}\n${pageUrl}` + (sources.length ? `\n\n公式出典\n${sources.map(source => `・${source.label}${source.date ? `（確認日：${source.date}）` : ''}\n  ${source.url}`).join('\n')}` : '');
  }

  document.querySelectorAll('[data-share-city]').forEach(button => button.addEventListener('click', () => {
    const dialog = ensureShareDialog();
    shareText.value = shareContents();
    shareStatus.textContent = '';
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
  }));
})();
