/* Match the national pages' font preference, within this browsing session. */
(() => {
  const root = document.documentElement;
  const buttons = document.querySelectorAll('[data-size-btn]');
  function apply(size) {
    root.classList.toggle('large', size === 'large');
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.sizeBtn === size)));
  }
  try { apply(sessionStorage.getItem('jk-national-size') || 'normal'); } catch (error) { apply('normal'); }
  buttons.forEach(button => button.addEventListener('click', () => {
    apply(button.dataset.sizeBtn);
    try { sessionStorage.setItem('jk-national-size', button.dataset.sizeBtn); } catch (error) {}
  }));
})();
