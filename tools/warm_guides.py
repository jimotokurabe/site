"""Apply the shared warm design to the two national help pages only."""
from bs4 import BeautifulSoup
from site_header import apply_site_header
from warm_components import family_hero


def fragment(html):
    return BeautifulSoup(html, 'html.parser')


def fold(soup, node, label):
    details = soup.new_tag('details', attrs={'class': 'guide-fold'})
    summary = soup.new_tag('summary')
    summary.string = label
    details.append(summary)
    node.replace_with(details)
    details.append(node)
    return details


def apply_warm_guide(html, family=False):
    soup = BeautifulSoup(html, 'html.parser')
    soup.body['class'] = ['warm-guide-page']
    mast = soup.select_one('.topbar')
    mast['class'] = ['mast']
    mast.select_one('.sizer')['class'] = ['size']
    # Replace the old persistent font preference with the shared session setting.
    for script in soup.select('script:not([src])'):
        if 'jk-size' in script.get_text():
            script.decompose()
    for link in soup.select('link[href]'):
        if 'fonts.google' in link['href']:
            link.decompose()
    boot = soup.new_tag('script')
    boot.string = "try{document.documentElement.classList.toggle('large',sessionStorage.getItem('jk-national-size')==='large')}catch(e){}"
    soup.head.append(boot)
    for asset in ('warm-shared.css', 'warm-guides.css'):
        soup.head.append(soup.new_tag('link', rel='stylesheet', href='assets/'+asset))
    apply_site_header(soup)
    soup.body.append(soup.new_tag('script', src='assets/warm-guides.js', defer=True))
    if family:
        warm_family(soup)
    else:
        warm_basic(soup)
    return str(soup)


def warm_basic(soup):
    hero = soup.select_one('.basic-hero')
    hero.select_one('.basic-answer').string = '本人の意思で進める、免許の自主返納。まずは移動・手続き・支援の3つを確認しましょう。'
    hero.select_one('.basic-jump').decompose()
    paths = [
        ('移動', '返納後の足を考える', '#flow', '<rect x="5" y="3" width="22" height="23" rx="4"/><path d="M5 15h22M11 4v11M21 4v11M8 26v3M24 26v3"/><circle cx="10" cy="21" r="1"/><circle cx="22" cy="21" r="1"/>'),
        ('手続き', '窓口・持ち物を調べる', '#region', '<path d="M9 3h12l6 6v20H5V3h4M20 3v8h7M10 17h12M10 23h9"/>'),
        ('支援', '地域の特典を確認する', '#after', '<rect x="4" y="7" width="24" height="19" rx="3"/><path d="M4 13h24M10 19l3 3 8-7"/>'),
    ]
    nav = soup.new_tag('nav', attrs={'class': 'guide-overview', 'aria-label': '返納前に確認する3つのこと'})
    for n, (label, text, href, drawing) in enumerate(paths, 1):
        nav.append(fragment(f'<a href="{href}"><svg viewBox="0 0 32 32" aria-hidden="true">{drawing}</svg><span class="guide-overview-label">0{n}　{label}</span><strong>{text}</strong><span aria-hidden="true">↓</span></a>').a)
    hero.append(nav)
    hero.append(fragment('<p class="guide-caution">返納が完了した後は運転できません。手続き当日の帰り道も先に決めましょう。</p>').p)
    hero.append(fragment('<p class="guide-planner-link"><a href="outing-plan.html">車なしのお出かけ計画を作る →</a></p>').p)
    region = soup.select_one('#region').extract()
    hero.insert_after(region)
    region.select_one('#basic-region-h').string = 'お住まいの手続き・特典を探す'
    region.find('p', recursive=False).string = '地域の公式案内へ'
    region.find_all('p', recursive=False)[1].string = '都道府県と市町村を選ぶと、警察の手続きや地域の支援へ進めます。'
    for node in soup.select('.basic-steps li'):
        body = node.select_one('p')
        fold(soup, body, '詳しく確認する')
    soup.select_one('#after').find_all('p', recursive=False)[-1].string = '対象年齢や申請期限などは、お住まいの市町村の情報で確認しましょう。'
    # Wording no longer assumes the region picker is below these sections.
    for node in soup.find_all(string=True):
        if '下の地域選択' in node:
            node.replace_with(str(node).replace('下の地域選択', 'このページの地域選択'))
    fold(soup, soup.select_one('.basic-check'), '警察の案内で確認する項目')


def warm_family(soup):
    hero = soup.select_one('.hk-hero')
    hero.select_one('h1').clear()
    hero.h1.append('家族への、最初のひと言。')
    hero.select_one('.hk-pref-picker').decompose()
    hero.select_one('.hk-note').decompose()
    hero.find_all('p', recursive=False)[1].string = '親の運転が心配なとき。6つの質問から、話しはじめの例を見つけられます。'
    stats = hero.select_one('.hk-stat').extract()
    intro = soup.new_tag('div', attrs={'class': 'guide-family-intro'})
    for node in list(hero.contents):
        intro.append(node.extract())
    intro.select_one('.hk-btn').string = '6つの質問をはじめる →'
    intro.append(fragment('<p class="hk-note">約1分・回答はサイトに送信されません</p>').p)
    hero.append(intro)
    hero.append(fragment(family_hero()).div)
    hero.append(fragment('<p class="guide-family-note">返納を決める前に、これからの移動を一緒に考えるための道具です。</p>').p)
    hero.append(fragment('<p class="guide-family-note"><a href="outing-plan.html">話した後は、車なしのお出かけ計画を作る →</a></p>').p)
    stats_fold = fragment('<details class="guide-fold guide-stat"><summary>全国の返納状況と出典</summary></details>').details
    stats_fold.append(stats)
    hero.append(stats_fold)
    result = soup.select_one('#hk-result')
    cards = result.select('.hk-card')
    risk, phrases, region, calc, about = cards
    risk.extract()
    phrases.insert_after(risk)
    phrases['class'].append('guide-phrase-card')
    title = phrases.find_all('h2')[-1].extract()
    title['tabindex'] = '-1'
    title['id'] = 'hk-result-title'
    phrases.insert(0, title)
    phrasebox = soup.select_one('#hk-phrases').extract()
    title.insert_after(phrasebox)
    more = soup.select_one('.hk-more-row').extract()
    phrasebox.insert_after(more)
    origin = fragment('<p class="hk-note">ひと言は、じもとくらべが作成した例です。</p>').p
    more.insert_after(origin)
    typebox = soup.new_tag('div')
    for node in [soup.select_one('.hk-type-line'), soup.select_one('#hk-type-text')]:
        typebox.append(node.extract())
    phrases.append(typebox)
    fold(soup, typebox, '回答に合わせた話し方のヒント')
    fold(soup, soup.select_one('.hk-ng'), '避けたい言い方を確認する')
    fold(soup, calc, '車と移動にかかるお金を比べる')
    fold(soup, about, 'このページの考え方・参考資料')
    for script in soup.select('script:not([src])'):
        text = script.get_text()
        if 'function renderResult(trigger)' in text:
            text = text.replace('show("hk-result");', 'show("hk-result"); $("hk-result-title").focus({preventScroll:true});')
            text = text.replace('if (navigator.clipboard) navigator.clipboard.writeText(x).then(done, done); else done();', 'var failed = function () { b.lastChild.textContent = "コピーできませんでした。文章を選択してコピーしてください"; };\n      if (navigator.clipboard) navigator.clipboard.writeText(x).then(done, failed); else failed();')
            script.string = text
