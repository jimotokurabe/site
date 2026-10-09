/* The plan stays in this document; no storage, URL parameters or requests. */
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
  function cost(key) {
    const input = $(key + '-cost');
    return input.value !== '' && input.validity.valid ? Number(input.value) : null;
  }
  function costText(key) { const amount = cost(key); return amount === null ? '未確認' : yen(amount); }
  function validateCosts() {
    for (const key of ['out', 'back']) {
      const input = $(key + '-cost');
      if (!input.validity.valid) {
        showStep(1);
        input.reportValidity();
        return false;
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
    $('step-' + index).focus();
  }
  function collect() {
    const purpose = document.querySelector('input[name="purpose"]:checked');
    const outCost = cost('out'), backCost = cost('back');
    const total = outCost !== null && backCost !== null ? yen(outCost + backCost) : '未確認（未入力の費用があります）';
    const groups = [
      ['行き', [['交通', mode('out')], ['時間・乗り場', shown('out-time')], ['片道の交通費', costText('out')]]],
      ['帰り', [['交通', mode('back')], ['時間・乗り場', shown('back-time')], ['片道の交通費', costText('back')]]],
      ['費用と準備', [['往復の交通費（1人）', total], ['行きと帰りの予約・送迎のお願い', value('booking')], ['雨の日・間に合わないとき', shown('backup')], ['持ち物・気になること', shown('note')]]]
    ];
    const checks = [];
    if (!value('place')) checks.push('行き先を決める');
    if (!value('day')) checks.push('出かける日・曜日を決める');
    for (const [key, label] of [['out', '行き'], ['back', '帰り']]) {
      if (mode(key) === '未定') checks.push(label + 'の交通を決める');
      if (!value(key + '-time')) checks.push(label + 'の時間・乗り場を調べる');
      if (cost(key) === null) checks.push(label + 'の交通費を確認する');
    }
    if ($('booking').selectedIndex === 0 || $('booking').selectedIndex === 2) checks.push('行きと帰りの予約・送迎のお願いを確認する');
    if (!value('backup')) checks.push('雨の日・予定が変わったときの代案を考える');
    checks.push('出発前に運行日・時刻・運賃をもう一度確かめる');
    return {purpose: purpose ? purpose.value : '未定', place: shown('place'), day: shown('day'), groups, checks};
  }
  function render() {
    const plan = collect();
    $('result-destination').textContent = plan.purpose + ' ／ ' + plan.place + ' ／ ' + plan.day;
    $('result-route').textContent = '家 → ' + plan.place + ' → 家';
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
    const lines = ['車なしのお出かけ計画', '目的：' + plan.purpose, '行き先：' + plan.place, '日・曜日：' + plan.day];
    for (const [title, fields] of plan.groups) {
      lines.push('', '【' + title + '】', ...fields.map(([label, text]) => label + '：' + text));
    }
    lines.push('', '【あとで確認すること】', ...plan.checks.map(text => '・' + text), '', '入力内容をまとめたメモです。運行・予約・運賃は利用前に公式案内で確認してください。', 'じもとくらべ https://jimotokurabe.jp/outing-plan.html');
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
      $('status').textContent = '計画をコピーしました。メモなどに貼り付けて使えます。';
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
    render(); $('result').hidden = false;
  });
  window.addEventListener('afterprint', () => {
    if (printHidden !== null) $('result').hidden = printHidden;
    printHidden = null;
  });
  app.hidden = false;
})();
