/* GA4: deploy with enhanced outbound/search/form/download/history measurement OFF.
   Only this module loads the production tag. No preview or debug bypass exists. */
(() => {
  'use strict';
  if (window.jkAnalytics || location.protocol !== 'https:' || location.port ||
      !['jimotokurabe.jp', 'www.jimotokurabe.jp'].includes(location.hostname) ||
      document.querySelector('meta[name="robots"][content*="noindex"]')) return;
  // Operator-only opt-out, set before loading a public page; never excludes an IP range.
  try { if (localStorage.getItem('jk-analytics-disabled') === '1') return; } catch (_) {}
  const id = 'G-T1PQ72Q40S';
  let ready = false, context = {}, region = {};
  const pending = [], seen = new Set();
  const features = new Set(['family_hint', 'city_guide', 'selected_supports', 'outing_plan', 'gomi_consultation', 'transport_cost']);
  function send(name, extra = {}, once = '') {
    if (!ready) { pending.push([name, extra, once]); return; }
    if (once && seen.has(once)) return;
    if (once) seen.add(once);
    window.gtag('event', name, {...context, ...region, ...extra});
  }
  // Inputs are internal enums / catalog-validated public IDs, never DOM input values.
  window.jkAnalytics = Object.freeze({
    memoCopied(feature) {
      if (features.has(feature)) send('memo_copy', {feature_type: feature});
    },
    transportRegion(pref, city, state) {
      if (!/^[a-z0-9-]{1,40}$/.test(pref) || !/^[a-z0-9-]{1,60}$/.test(city) ||
          !['supported', 'unsupported', 'error'].includes(state)) return;
      region = {city_id: pref + ':' + city, estimate_status: state};
      send('transport_region_view', {...region}, 'region:' + region.city_id + ':' + state);
    },
    clearTransportRegion() { region = {}; },
    estimateShown() {
      if (region.estimate_status === 'supported')
        send('transport_estimate_view', {...region}, 'estimate:' + region.city_id);
    }
  });
  function boot() {
    const canonical = document.querySelector('link[rel="canonical"]');
    let page;
    try { page = new URL(canonical.href); } catch (_) { return; }
    if (page.origin !== 'https://jimotokurabe.jp') return;
    page.search = ''; page.hash = '';
    const path = page.pathname;
    const city = path.match(/^\/([a-z0-9-]+)-(menkyo-henno|mobility|gomi-support)\/([a-z0-9-]+)\.html$/);
    const pageType = city ? (city[2] === 'gomi-support' ? 'gomi_detail' : 'city_detail') :
      path === '/transport-cost.html' ? 'transport_cost' : path === '/outing-plan.html' ? 'outing_plan' :
      path === '/henno-hanashikata.html' ? 'family_guide' : path === '/' ? 'home' : 'other';
    const memo = !!document.querySelector('#warm-family-dialog, #selection-copy, [data-share-city], #outing-copy, [data-gomi-copy], #tc-copy, #hk-phrases');
    let referrer = '';
    try {
      const ref = new URL(document.referrer);
      // Preserve source domain only; no search query, previous input, local preview URL or path.
      if (['https:', 'http:'].includes(ref.protocol) && !['localhost','127.0.0.1','[::1]'].includes(ref.hostname)) referrer = ref.origin + '/';
    } catch (_) {}
    context = {page_location: page.href, page_path: path, page_referrer: referrer,
      page_title: document.title, page_type: pageType, memo_available: memo ? 'yes' : 'no'};
    if (city) context.city_id = city[1] + ':' + city[3];
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    window.gtag('config', id, {...context, allow_google_signals: false, allow_ad_personalization_signals: false});
    ready = true;
    pending.splice(0).forEach(args => send(...args));
    const script = document.createElement('script');
    script.async = true; script.src = 'https://www.googletagmanager.com/gtag/js?id=' + id;
    document.head.append(script);
  }
  document.addEventListener('click', event => {
    const control = event.target?.closest?.('a, button');
    if (!control) return;
    if (control.matches('[data-print], [data-gomi-print], #tc-print, #outing-print')) { send('print_request'); return; }
    if (control.tagName !== 'A' || !control.closest('main')) return;
    const href = control.getAttribute('href') || '';
    if (href.startsWith('tel:')) { send('phone_click'); return; }
    let url; try { url = new URL(href, location.href); } catch (_) { return; }
    if (!['http:', 'https:'].includes(url.protocol)) return;
    if (url.hostname === 'line.me' && url.pathname.startsWith('/R/share')) { send('share_line'); return; }
    const officialDomain = /(^|\.)(lg|go)\.jp$/.test(url.hostname) || /(^|\.)(city|town|vill|pref)\.[a-z0-9-]+(?:\.[a-z0-9-]+)?\.jp$/.test(url.hostname) || /(^|\.)nishi\.or\.jp$/.test(url.hostname);
    // Publisher-marked source links include transport operators, not arbitrary external links.
    const source = control.matches('[data-official-source]') || control.closest('.record-fields, .gomi-route-sources, .sources, .basic-source');
    if (url.origin !== location.origin && (officialDomain || source)) {
      send('official_info_click', {link_domain: url.hostname});
    } else if (control.closest('[data-related-support]') && url.origin === location.origin) {
      send('related_support_click');
    }
  });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, {once: true});
  else boot();
})();
