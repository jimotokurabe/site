(() => {
  const menu = document.querySelector('.site-menu');
  if (!menu) return;
  const summary = menu.querySelector('summary');
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menu.open) {
      menu.open = false;
      summary.focus();
    }
  });
  document.addEventListener('click', event => {
    if (menu.open && !menu.contains(event.target)) menu.open = false;
  });
  menu.querySelectorAll('a[href]').forEach(link => link.addEventListener('click', () => {
    menu.open = false;
    // Do not leave keyboard focus in the now-hidden menu after a local jump.
    if (link.getAttribute('href').startsWith('#')) {
      const target = document.getElementById(link.hash.slice(1));
      if (target) {
        target.setAttribute('tabindex', '-1');
        target.focus({preventScroll: true});
      }
    }
  }));
})();
