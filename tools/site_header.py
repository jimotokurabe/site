"""Put region navigation ahead of optional display controls."""
from bs4 import BeautifulSoup


def apply_site_header(soup, base='', home=False):
    mast = soup.select_one('.mast')
    if mast is None:
        return
    # Keep the original controls and identifiers: existing size/print handlers
    # and the shared session preference must keep working on custom city pages.
    controls = mast.select_one('.size, .utilities')
    brand = mast.select_one('.brand')
    if controls is None or brand is None:
        raise ValueError('Expected brand and display controls in national header')
    controls.extract()
    controls['class'] = ['site-display-controls']
    controls['role'] = 'group'
    controls['aria-label'] = '文字の大きさ'
    brand.extract()
    mast.clear()
    mast['class'] = ['mast', 'site-mast']
    mast.append(brand)
    region = soup.new_tag('a', href='#prefectures' if home else base+'index.html#prefectures', attrs={'class': 'site-region-link'})
    region.string = '地域を探す'
    mast.append(region)
    menu = BeautifulSoup('''<details class="site-menu"><summary>メニュー</summary><div class="site-menu-panel"><nav aria-label="サイトの案内"></nav><section class="site-display"><h2>表示設定</h2></section></div></details>''', 'html.parser').details
    nav = menu.nav
    switch = soup.select_one('.city-switch')
    if switch:
        local = switch.find_all('a')[-1]
        nav.append(local.extract())
        switch.decompose()
    for label, href in (
        ('車なしのお出かけ計画', base+'outing-plan.html'),
        ('免許返納の手続き', base+'menkyo-henno-guide.html'),
        ('家族と確認する' if soup.select_one('#family') else '家族への話し方', '#family' if soup.select_one('#family') else base+'henno-hanashikata.html'),
    ):
        link = soup.new_tag('a', href=href)
        link.string = label
        nav.append(link)
    menu.select_one('.site-display').append(controls)
    # Printing belongs to page actions, not to the font-size group.
    for button in controls.select('.print'):
        menu.select_one('.site-display').append(button.extract())
    mast.append(menu)
    for redundant in soup.select('.hero-tools'):
        redundant.decompose()
    soup.head.append(soup.new_tag('link', rel='stylesheet', href=base+'assets/site-header.css'))
    soup.body.append(soup.new_tag('script', src=base+'assets/site-header.js', defer=True))
