"""A more colorful welcome for the home page, without changing its search data."""
from bs4 import BeautifulSoup


def fragment(markup):
    return BeautifulSoup(markup, 'html.parser')


def apply_colorful_home(soup):
    soup.body['class'] = [*soup.body.get('class', []), 'colorful-home']
    soup.head.append(soup.new_tag('link', rel='stylesheet', href='assets/colorful-home.css'))
    hero = soup.select_one('.warm-home-hero')
    hero.h1.clear()
    hero.h1.append(fragment('免許返納の特典を、<br><span>お住まいの地域から。</span>'))
    hero.select_one('.lead').string = 'バス・タクシーの支援や、通院・買い物の足を、市町村ごとに。'
    hero.select_one('.reassure').clear()
    hero.select_one('.reassure').append(fragment('<span class="home-check" aria-hidden="true">✓</span> 返納前でも使える支援を案内します。'))
    portrait = hero.select_one('.warm-portrait img')
    portrait['src'] = 'assets/family-home-color.webp'
    portrait['alt'] = '親子で地域の案内を読み、これからの外出を相談するイラスト'
    portrait['width'], portrait['height'] = '1536', '1024'
    portrait['fetchpriority'] = 'high'
    hero.select_one('.warm-speech').clear()
    hero.select_one('.warm-speech').append(fragment('これからのお出かけ、<br>一緒に考えてみよう。'))
    directory = soup.select_one('#prefectures')
    directory.select_one('.section-head h2').insert(0, fragment('<svg class="home-pin" viewBox="0 0 32 32" aria-hidden="true"><path d="M16 29S5 19 5 12a11 11 0 0 1 22 0c0 7-11 17-11 17Z"/><circle cx="16" cy="12" r="4"/></svg>'))
    for i, button in enumerate(directory.select('.region-toggle')):
        button['data-home-tone'] = str(i % 4)
    support = soup.select_one('.four').parent
    support['class'] = [*support.get('class', []), 'home-support']
    intro = soup.new_tag('div', attrs={'class': 'home-support-intro'})
    copy = soup.new_tag('div')
    copy.append(support.h2.extract())
    copy.append(support.select_one('p.muted').extract())
    intro.append(copy)
    intro.append(fragment('<img src="assets/town-mobility-home.webp" alt="バスや買い物のお店がある、暮らしのまちのイラスト" width="1536" height="1024" loading="lazy" decoding="async">').img)
    support.insert(0, intro)
    drawings = [
        '<rect x="4" y="7" width="24" height="19" rx="3"/><path d="M4 13h24M10 19l3 3 8-7"/>',
        '<rect x="5" y="3" width="22" height="23" rx="4"/><path d="M5 15h22M11 4v11M21 4v11M8 26v3M24 26v3"/><circle cx="10" cy="21" r="1"/><circle cx="22" cy="21" r="1"/>',
        '<path d="M4 16l3-8h18l3 8v10H4ZM4 16h24M12 8V4h8v4M7 26v3M25 26v3"/><circle cx="9" cy="21" r="1"/><circle cx="23" cy="21" r="1"/>',
        '<path d="M4 15l12-11 12 11M8 12v16h16V12M13 28V18h6v10"/>',
    ]
    for article, drawing in zip(support.select('.four article'), drawings):
        article.insert(0, fragment(f'<svg class="home-support-icon" viewBox="0 0 32 32" aria-hidden="true">{drawing}</svg>'))
    # Keep the family conversation action and its existing dialog handlers.
    family = soup.select_one('.warm-family')
    family.select_one('img')['src'] = 'assets/family-home-color.webp'
    family.select_one('img')['loading'] = 'lazy'
