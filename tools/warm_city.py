"""Apply shared visual composition without changing municipal source records."""
from bs4 import BeautifulSoup
from warm_components import family_dialog


def apply_warm_city(soup):
    for filename in ('warm-shared.css', 'warm-city.css'):
        soup.head.append(soup.new_tag('link', rel='stylesheet', href='../assets/' + filename))
    layout = soup.select_one('.layout')
    content = layout.select_one('.content')
    nav = layout.select_one('.side')
    if nav:
        disclosure = soup.new_tag('details', attrs={'class': 'warm-page-nav'})
        summary = soup.new_tag('summary')
        summary.string = 'このページで確認できること'
        disclosure.append(summary)
        disclosure.append(nav.extract())
        content.insert(0, disclosure)
    answer = soup.select_one('.search-answer')
    if answer:
        answers = soup.new_tag('details', attrs={'class': 'warm-page-nav warm-answers'})
        title = soup.new_tag('summary')
        title.string = 'よくある疑問と、掲載情報の要点'
        answers.append(title)
        answers.append(answer.extract())
        content.insert(1, answers)
    sidebar = soup.new_tag('aside', attrs={'class': 'warm-sidebar', 'aria-label': '家族と一緒に確認'})
    sidebar.append(BeautifulSoup('''<section class="warm-aside-intro"><p class="eyebrow">家族で話す、最初のひとこと</p><blockquote>「これからのお出かけ、<br>一緒に考えてみよう。」</blockquote><img src="../assets/family-guide.webp" width="1536" height="1024" alt="親子で地域の案内を確認しているイラスト" loading="lazy"><button type="button" data-family-open>話し始めるヒント</button></section>''', 'html.parser'))
    family = soup.select_one('#family')
    if family:
        sidebar.append(family.extract())
        share = soup.new_tag('button', attrs={'type': 'button', 'data-share-city': ''})
        share.string = '家族に共有するメモを作る'
        family.append(share)
    layout.append(sidebar)
    soup.body.append(BeautifulSoup(family_dialog(), 'html.parser'))
    soup.body.append(soup.new_tag('script', src='../assets/warm-experience.js', defer=True))
