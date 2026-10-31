(() => {
  'use strict';
  const comparison = document.querySelector('.pref-comparison');
  if (!comparison) return;
  const unit = comparison.dataset.municipalUnit || '市区町村';
  const input = document.getElementById('city-query'), area = document.getElementById('area');
  const groups = [...comparison.querySelectorAll('[data-comparison-kind]')];
  const choices = [...document.querySelectorAll('[name="comparison-kind"]')];
  const normalize = text => text.normalize('NFKC').toLowerCase().replace(/[ァ-ヶ]/g, c => String.fromCharCode(c.charCodeAt(0)-96)).replace(/\s/g, '');
  const tokens = () => input.value.trim().split(/[\s,、，]+/).filter(Boolean).map(normalize);
  function matches(element, terms) {
    return (!area.value || element.dataset.region === area.value) && (!terms.length || terms.some(term =>
      [element.dataset.name, element.dataset.kana].some(value => normalize(value || '').includes(term))));
  }
  function filter() {
    const terms = tokens(), kind = choices.find(choice => choice.checked)?.value || 'return';
    const cities = new Set(); let count = 0;
    groups.forEach(group => {
      const visible = kind === 'all' || group.dataset.comparisonKind === kind;
      group.hidden = !visible;
      group.querySelectorAll('[data-comparison-row]').forEach(row => {
        row.hidden = !matches(row, terms);
        if (visible && !row.hidden) { count++; cities.add(row.dataset.city); }
      });
    });
    document.getElementById('comparison-count').textContent = `${cities.size}${unit}・${count}件の掲載記録を表示しています。`;
    document.getElementById('comparison-empty').hidden = count !== 0;
    let total = 0;
    document.querySelectorAll('.city-group').forEach(group => {
      let found = 0;
      group.querySelectorAll('li').forEach(item => {
        item.hidden = !matches({dataset:{...item.dataset, region:group.dataset.region}}, terms);
        if (!item.hidden) found++;
      });
      group.hidden = !found; total += found;
    });
    document.getElementById('count').textContent = `${total}${unit}を表示しています。`;
    document.getElementById('empty').hidden = total !== 0;
  }
  let composing = false;
  input.addEventListener('compositionstart', () => { composing = true; });
  input.addEventListener('compositionend', () => { composing = false; filter(); });
  input.addEventListener('input', () => { if (!composing) filter(); });
  area.addEventListener('change', filter); choices.forEach(choice => choice.addEventListener('change', filter));
  document.getElementById('filter-form').addEventListener('submit', event => {
    event.preventDefault(); filter();
    const target = document.getElementById('comparison-title'); target.tabIndex = -1; target.focus();
  });
  function reset() { input.value = ''; area.value = ''; filter(); input.focus(); }
  document.getElementById('reset').addEventListener('click', reset);
  document.getElementById('empty-reset').addEventListener('click', reset);
  function revealHash() {
    let id; try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    const target = document.getElementById(id); if (!target) return;
    const group = target.closest('[data-comparison-kind]');
    if (group) { choices.find(choice => choice.value === group.dataset.comparisonKind).checked = true; filter(); }
    for (let parent = target.parentElement; parent; parent = parent.parentElement) if (parent.tagName === 'DETAILS') parent.open = true;
  }
  window.addEventListener('hashchange', revealHash);
  let printDetails = [];
  window.addEventListener('beforeprint', () => {
    printDetails = [...comparison.querySelectorAll('details')].map(element => [element, element.open]);
    printDetails.forEach(([element]) => { element.open = true; });
  });
  window.addEventListener('afterprint', () => { printDetails.forEach(([element, open]) => { element.open = open; }); });
  document.body.classList.add('has-pref-comparison'); filter(); revealHash();
})();
