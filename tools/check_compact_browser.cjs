// Browser checks for the nationwide compact layout. Serve the repository first.
const {chromium} = require('playwright');
const fs = require('fs');
const path = require('path');
const base = process.env.PREVIEW_URL || 'http://127.0.0.1:8766';
const output = path.resolve(process.env.QA_OUT || 'preview/national-qa');
const cities = [
  'hyogo/kobe', 'okinawa/ogimi', 'fukui/eiheiji', 'kanagawa/yokohama',
  'kagoshima/kagoshima', 'hyogo/nishinomiya', 'tokyo/shibuya', 'tokyo/setagaya',
  'aichi/nagoya', 'hokkaido/sapporo', 'hyogo/kawanishi', 'hyogo/akashi'
];
(async () => {
  fs.mkdirSync(output, {recursive:true});
  const executablePath = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  const browser = await chromium.launch({headless:true, ...(fs.existsSync(executablePath) ? {executablePath} : {})});
  const report = [];
  for (const city of cities) {
    const [pref, slug] = city.split('/');
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    // Local checks must not fetch external analytics/fonts or log real traffic.
    await page.route('**/*', route => route.request().url().startsWith(base)
      ? route.continue() : route.abort());
    await page.goto(`${base}/${pref}-menkyo-henno/${slug}.html`);
    for (const width of [320,390,1440]) {
      await page.setViewportSize({width,height:1000});
      for (const scale of ['standard','large','200%']) {
        await page.evaluate(scale => {
          document.documentElement.classList.toggle('large',scale==='large');
          document.documentElement.style.fontSize=scale==='200%'?'36px':'';
        },scale);
        const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
        report.push({city,width,scale,overflow});
      }
    }
    await page.evaluate(()=>{document.documentElement.classList.remove('large');document.documentElement.style.fontSize='';});
    for (const width of [390,1440]) {
      await page.setViewportSize({width,height:1000});
      await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
      if (cities.indexOf(city)<5) await page.screenshot({path:path.join(output,`${pref}-${slug}-${width}.png`)});
    }
    const checks = page.locator('#family .checklist input[type=checkbox]');
    await checks.first().check();await page.reload();
    const saved=await checks.first().isChecked();
    await page.locator('[data-share-city]').click();
    const memo=await page.locator('[data-share-text]').inputValue();
    const sharedSource=memo.includes('公式出典');
    await page.locator('[data-share-close]').click();
    await page.locator('[data-family-open]').click();
    const family=await page.locator('dialog[open]').count()===1;
    await page.keyboard.press('Escape');
    const printing=await page.evaluate(()=>{
      const previous=[...document.querySelectorAll('details')].map(x=>x.open);
      window.dispatchEvent(new Event('beforeprint'));
      const expanded=[...document.querySelectorAll('details')].every(x=>x.open);
      window.dispatchEvent(new Event('afterprint'));
      return expanded && [...document.querySelectorAll('details')].every((x,i)=>x.open===previous[i]);
    });
    report.push({city,errors,saved,sharedSource,family,printing});
    await page.close();
  }
  // Shared sections must remain readable at narrow widths and enlarged text.
  const prefFiles=fs.readdirSync('data').filter(x=>x.endsWith('-menkyo-henno.json'));
  const page=await browser.newPage({viewport:{width:320,height:1000}});
  await page.route('**/*',route=>route.request().url().startsWith(base)?route.continue():route.abort());
  for(const file of prefFiles){
    const pref=file.replace('-menkyo-henno.json','');
    await page.goto(`${base}/${pref}-menkyo-henno.html#return-procedure`);
    const section=page.locator('#return-procedure');
    const exists=await section.count()===1;
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
    report.push({pref,exists,overflow});
  }
  await browser.close();
  const failures=report.filter(x=>x.overflow || x.exists===false || (x.errors &&
    (x.errors.length || !x.saved || !x.sharedSource || !x.family || !x.printing)));
  fs.writeFileSync(path.join(output,'browser-check.json'),JSON.stringify({checks:report,failures},null,2));
  console.log(JSON.stringify({checks:report.length,failures},null,2));
  if(failures.length)process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});
