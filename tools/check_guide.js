// 手順ページ（hyogo-menkyo-henno/<slug>.html）を、ブラウザで開いて確かめる。
// 見ること：横にはみ出さないか（スマホの幅・文字を大きく・折りたたみを開いた状態）、
// コピー・印刷・LINEのボタン、一覧ページからの入口、印刷したときの枚数（A4で2枚まで）、
// 申し込み期限の計算欄（あるページだけ）。
//
// 使い方（ページを作ったフォルダを 127.0.0.1 で配ってから）:
//   NODE_PATH=$(npm root -g) BASE=http://127.0.0.1:8765 PAGE=kawanishi node tools/check_guide.js
// PDF_OUT=印刷.pdf を付けると、印刷の見た目をPDFで保存する。問題があれば終了コード1で終わる。
const { chromium } = require('playwright');

const BASE = (process.env.BASE || 'http://127.0.0.1:8765').replace(/\/$/, '');
const PAGE = process.env.PAGE;
const MAX_PRINT_PAGES = 2;

async function sideScroll(page) {
  return page.evaluate(() => {
    const vw = document.documentElement.clientWidth, over = [];
    document.querySelectorAll('body *').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.right > vw + 1 && !el.closest('.table-scroll table')) over.push(el.tagName.toLowerCase() + '.' + el.className);
    });
    return { scrolls: document.documentElement.scrollWidth > vw, over: over.slice(0, 5) };
  });
}

(async () => {
  if (!PAGE) throw new Error('PAGE（市町の slug）を指定してください');
  const url = `${BASE}/${process.env.DIR || 'hyogo-menkyo-henno'}/${PAGE}.html`;  // DIR=osaka-menkyo-henno など
  const browser = await chromium.launch();
  const out = {};
  const ng = [];

  // 1) ふつうのスマホ（クリップボードが使える）
  let ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  await ctx.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: BASE });
  let page = await ctx.newPage();
  await page.addInitScript(() => { window.__printed = 0; window.print = () => { window.__printed++; }; });
  const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  out.status = resp.status();
  out.h1 = ((await page.textContent('h1')) || '').trim();
  out.canonical = await page.getAttribute('link[rel="canonical"]', 'href');
  out.noindex = (await page.$('meta[name="robots"]')) !== null;
  out.sideScroll = await sideScroll(page);

  await page.bringToFront();
  await page.click('[data-copy]');
  await page.waitForTimeout(500);
  out.copyMsg = await page.textContent('#copied');
  out.clipboard = await page.evaluate(() => navigator.clipboard.readText()).catch(e => 'ERR ' + e.message);
  await page.click('[data-print]');
  out.printCalled = await page.evaluate(() => window.__printed);
  const line = await page.getAttribute('a[href^="https://line.me/"]', 'href');
  out.lineText = decodeURIComponent((line || '').split('text=')[1] || '');
  out.tels = await page.$$eval('a[href^="tel:"]', as => [...new Set(as.map(a => a.getAttribute('href')))]);

  // 申し込み期限の計算欄があるページは、日付を入れて答えが出るか
  if (await page.$('#deadline')) {
    await page.fill('#calc-date', new Date().toISOString().slice(0, 10));
    await page.dispatchEvent('#calc-date', 'change');
    out.calc = { visible: await page.isVisible('#deadline'), state: await page.getAttribute('#deadline', 'data-state'),
                 text: ((await page.textContent('#calc-out strong')) || '').trim() };
  }

  await page.click('[data-size-btn="large"]');
  await page.evaluate(() => document.querySelectorAll('details').forEach(d => { d.open = true; }));
  out.largeOpen = await sideScroll(page);
  await ctx.close();

  // 2) クリップボードが使えないブラウザ（URLを出して、手でコピーしてもらう）
  ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  page = await ctx.newPage();
  await page.addInitScript(() => { Object.defineProperty(navigator, 'clipboard', { value: undefined }); });
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.click('[data-copy]');
  out.fallbackBox = (await page.isVisible('#copy-url')) ? await page.inputValue('#copy-url') : '';
  await ctx.close();

  // 3) 一覧ページのカードから、手順ページへ行けるか
  ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  page = await ctx.newPage();
  await page.goto(`${BASE}/hyogo-menkyo-henno.html`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.click(`#${PAGE} .btn-guide`);
  await page.waitForLoadState('domcontentloaded');
  out.fromList = page.url();
  await ctx.close();

  // 4) 印刷（A4）の枚数
  ctx = await browser.newContext();
  page = await ctx.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  const pdf = await page.pdf({ path: process.env.PDF_OUT, preferCSSPageSize: true });
  out.printPages = (pdf.toString('latin1').match(/\/Type\s*\/Page(?![s\w])/g) || []).length;
  await ctx.close();
  await browser.close();

  if (out.status !== 200) ng.push('ページが開けない');
  if (!out.h1) ng.push('見出し（h1）がない');
  if (out.sideScroll.scrolls || out.largeOpen.scrolls) ng.push('横にはみ出す');
  if (!/コピーしました/.test(out.copyMsg || '') || out.clipboard !== out.canonical) ng.push('URLのコピー');
  if (out.printCalled !== 1) ng.push('印刷ボタン');
  if (!out.lineText.includes(out.canonical)) ng.push('LINEで送る');
  if (out.fallbackBox !== out.canonical) ng.push('コピーできないときの表示');
  if (!out.fromList.endsWith(`/hyogo-menkyo-henno/${PAGE}.html`)) ng.push('一覧ページからの入口');
  if (out.printPages < 1 || out.printPages > MAX_PRINT_PAGES) ng.push(`印刷が${out.printPages}枚`);
  if (out.calc && !(out.calc.visible && out.calc.state && out.calc.text)) ng.push('申し込み期限の計算');
  out.ng = ng;
  console.log(JSON.stringify(out, null, 1));
  process.exit(ng.length ? 1 : 0);
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
