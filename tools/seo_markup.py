"""検索エンジンと共有サービス向けの裏側の記述を、生成したページに足す。

- og:image：LINE・X などでリンクを貼ったときに出る画像（assets/og-image.png）
- 構造化データ（JSON-LD）：検索エンジンにページの階層（パンくず）と、
  冒頭の質問・回答（FAQ）を機械が読める形で伝える。
  本文に見えている内容だけを使い、新しい事実は書かない。
"""
import json
from urllib.parse import urljoin
from bs4 import BeautifulSoup

SITE = 'https://jimotokurabe.jp/'
OG_IMAGE = SITE + 'assets/og-image.png'
OG_IMAGE_ALT = 'じもとくらべ：免許返納の特典・バス・タクシーの支援を市町村ごとに、公式ページで確かめて比べる'
CRUMB_LABELS = {'現在の場所', 'いまいる場所', 'パンくず'}
MARK = 'data-seo-markup'


def page_url(relative):
    return SITE + ('' if relative == 'index.html' else relative)


def normalize(url):
    """トップは canonical と同じ https://jimotokurabe.jp/ にそろえる。"""
    return SITE if url == SITE + 'index.html' else url


def short_title(title):
    return title.split('｜')[0].strip()


def _text(node):
    return node.get_text(' ', strip=True)


def breadcrumbs(soup, relative, title):
    nav = next((n for n in soup.find_all('nav') if n.get('aria-label') in CRUMB_LABELS), None)
    if nav is None:
        return None
    links = nav.find_all('a', href=True)
    items = [(_text(a), normalize(urljoin(page_url(relative), a['href']))) for a in links]
    current = nav.find(attrs={'aria-current': 'page'})
    if current:
        name = _text(current)
    else:
        # 「トップ ＞ 東京都」のように、最後のリンクの後ろに現在地の文字だけがある書き方
        trailing = ''.join(t for t in links[-1].next_siblings if isinstance(t, str)) if links else ''
        name = trailing.replace('＞', '').replace('›', '').replace('/', '').strip() or short_title(title)
    items.append((name, page_url(relative)))
    if len(items) < 2:
        return None
    return {'@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': u} for i, (n, u) in enumerate(items)]}


def faq(soup):
    pairs = []
    for item in soup.select('.answer-item'):
        q = item.find('h3')
        a = item.select_one('.answer-text')
        if q and a and _text(q) and _text(a):
            pairs.append((_text(q), _text(a)))
    if not pairs:
        return None
    return {'@type': 'FAQPage', 'mainEntity': [
        {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in pairs]}


def website():
    return {'@type': 'WebSite', 'name': 'じもとくらべ', 'url': SITE, 'inLanguage': 'ja',
            'description': '市町村ごとにちがう免許返納の特典・バス助成・タクシー支援を、公式ページで確かめて同じ項目で比べるサイト'}


def markup(soup, relative):
    """ページに足す <head> 用の記述を文字列で返す。すでにある分は足さない。"""
    out = []
    if not soup.select_one('meta[property="og:image"]'):
        out += [f'<meta property="og:image" content="{OG_IMAGE}">',
                '<meta property="og:image:width" content="1200">',
                '<meta property="og:image:height" content="630">',
                f'<meta property="og:image:alt" content="{OG_IMAGE_ALT}">',
                '<meta name="twitter:card" content="summary_large_image">']
    noindex = soup.select_one('meta[name="robots"]')
    indexable = not (noindex and 'noindex' in (noindex.get('content') or ''))
    if indexable and not soup.select_one(f'script[{MARK}]'):
        title = soup.title.get_text(strip=True) if soup.title else ''
        graph = []
        if relative == 'index.html':
            graph.append(website())
        for item in (breadcrumbs(soup, relative, title), faq(soup)):
            if item:
                graph.append(item)
        if graph:
            data = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False)
            out.append(f'<script type="application/ld+json" {MARK}>{data.replace("</", "<\\/")}</script>')
    return '\n'.join(out)


def inject(html, relative):
    """文字列のまま持っているページに足す（元の書き方を変えないため、</head> の前に差し込む）。"""
    if '</head>' not in html:
        return html
    extra = markup(BeautifulSoup(html, 'html.parser'), relative)
    return html.replace('</head>', extra + '\n</head>', 1) if extra else html


def apply(soup, relative):
    """BeautifulSoup で持っているページに足す。"""
    extra = markup(soup, relative)
    if extra and soup.head:
        soup.head.append(BeautifulSoup(extra, 'html.parser'))
