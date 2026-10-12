"""Build the research preview for municipal waste collection support."""
from __future__ import annotations

from html import escape
import json
import re

from bs4 import BeautifulSoup


FIELD_LABELS = {
    'waste_scope': '対象となるごみ', 'collection_location': '回収場所',
    'indoor_carry': '室内からの搬出', 'eligibility': '対象条件',
    'family_help': '家族・周囲の手伝い', 'fees': '費用', 'limits': '点数・重量などの制限',
    'application': '申込み方法', 'attendance': '立会い・当日の対応', 'contact': '相談・申込先',
}
FIELD_ORDER = tuple(FIELD_LABELS)
FIELD_STATES = {
    'explicit': ('確認できた内容', 'known'),
    'explicit_exclusion': ('対象外の案内', 'excluded'),
    'not_stated': ('公式案内に記載なし', 'unknown'),
    'not_found': ('今回確認した資料では見つからず', 'not-found'),
    'conflicting': ('資料間で基準に差があります', 'conflict'),
    'needs_confirmation': ('窓口への確認が必要', 'unknown'),
}
KIND_LABELS = {
    'daily_support': '日常のごみ出し支援',
    'bulky_carry_support': '粗大ごみの室内搬出',
    'regular_bulky': '通常の粗大ごみ収集',
    'self_dropoff': '施設への自己搬入',
}
KIND_ORDER = tuple(KIND_LABELS)


def _e(value):
    return escape(str(value), quote=True)


def _slug(city):
    pref, slug = city['id'].split(':', 1)
    return f'{pref}-gomi-support/{slug}.html'


LOGIC_LABELS = {'all': '次の条件をすべて満たす必要があります', 'any': '次のいずれかを満たす必要があります', 'exception': '例外・相談', 'exclusion': '対象外となる条件', 'note': '申請・確認について'}


def _value(value):
    """Plain-text conditions retain both group boundaries and AND/OR for memos."""
    if value is None:
        return '未確認'
    if value is True:
        return '対象条件・作業条件を満たす場合に対応'
    if value is False:
        return 'いいえ（対象外）'
    if isinstance(value, (list, tuple)):
        return '\n'.join('・' + _value(v).replace('\n', '\n  ') for v in value)
    if isinstance(value, dict):
        parts = [str(value['label'])] if value.get('label') else []
        for key, child in value.items():
            if key == 'label':
                continue
            parts.append(LOGIC_LABELS.get(key, key) + '：\n' + _value(child))
        return '\n'.join(parts)
    return str(value)


def _value_html(value):
    """Render the same nested condition tree as readable groups, never flatten it."""
    if isinstance(value, (list, tuple)):
        return '<ul class="gomi-condition-list">' + ''.join('<li>' + _value_html(v) + '</li>' for v in value) + '</ul>'
    if isinstance(value, dict):
        parts = [f'<p class="gomi-condition-title"><strong>{_e(value["label"])}</strong></p>'] if value.get('label') else []
        for key, child in value.items():
            if key == 'label':
                continue
            parts.append(f'<div class="gomi-condition-group" data-condition="{_e(key)}"><p class="gomi-condition-operator">{_e(LOGIC_LABELS.get(key, key))}</p>{_value_html(child)}</div>')
        return ''.join(parts)
    return _e(_value(value))


def _questions_html(questions, *, common=False):
    if not questions:
        return ''
    css = 'gomi-common-questions' if common else 'gomi-service-questions'
    title = '市内の各方法に共通する確認事項' if common else 'この方法について問い合わせること'
    return f'<section class="gomi-questions {css}"><h4>{title}</h4><ul>' + ''.join(f'<li>{_e(q)}</li>' for q in questions) + '</ul></section>'


def _field_html(key, item, source_map, source_numbers, source_keys):
    state = item.get('state', 'not_stated')
    state_label, state_class = FIELD_STATES.get(state, ('状態を確認してください', 'unknown'))
    content = _value(item.get('value'))
    if state == 'not_found':
        content = item.get('value') or '今回確認した公式資料では、該当する制度を確認できませんでした。制度がないことを示すものではありません。'
    if state == 'not_stated' and item.get('value') is None:
        content = '—'
    source_ids = [sid for sid in item.get('source_ids', []) if sid in source_numbers]
    refs = ' '.join(f'<a href="#source-{_e(source_keys[sid])}" aria-label="出典 {source_numbers[sid]}">[{source_numbers[sid]}]</a>' for sid in source_ids)
    display = _value_html(item.get('value')) if isinstance(item.get('value'), (dict, list)) else _e(content)
    if key == 'contact':
        display = re.sub(r'0\d{1,4}-\d{1,4}-\d{3,4}', lambda m: f'<a href="tel:{m[0]}">{m[0]}</a>', display)
    links = ''.join(f'<a class="gomi-contact-link" href="{_e(source_map[link["source_id"]]["url"])}" target="_blank" rel="noopener">{_e(link["label"])}</a>' for link in item.get('links', []))
    cite_html = '<div class="gomi-field-sources"><span>根拠：</span>' + (refs or '<span>出典未登録</span>') + '</div>'
    return (f'<div class="gomi-fact gomi-state-{_e(state_class)}" data-field="{_e(key)}" data-source-ids="{_e(" ".join(source_keys[sid] for sid in source_ids))}">'
            f'<dt>{_e(FIELD_LABELS.get(key,key))}<span class="gomi-state-label">{_e(state_label)}</span></dt>'
            f'<dd><div class="gomi-field-value" data-memo-value="{_e(content)}">{display}</div>{links}{cite_html}</dd></div>')


def _service_html(service, source_map, checked, human_reviewed):
    kind = service.get('kind', '')
    fields = service.get('fields', {})
    used_ids = []
    for field in fields.values():
        for sid in field.get('source_ids', []):
            if sid in source_map and sid not in used_ids:
                used_ids.append(sid)
    source_numbers = {sid: i + 1 for i, sid in enumerate(used_ids)}
    source_keys = {sid: f'{service["id"]}--{sid}' for sid in used_ids}
    fact_html = {key: _field_html(key, fields.get(key, {'state':'not_stated','value':None,'source_ids':[]}), source_map, source_numbers, source_keys) for key in FIELD_ORDER}
    facts = ''.join(fact_html.values())
    review_date = service.get('checked') or checked or '未記載'
    notes = ''
    if service.get('search_scope'):
        scope = service['search_scope']
        notes = '<p class="gomi-search-scope"><strong>今回の確認範囲：</strong>' + _e(_value(scope)) + '</p>'
    evidence = service.get('evidence_status', '')
    banner = ''
    if evidence == 'searched_not_found':
        banner = '<p class="gomi-not-found"><strong>該当制度を確認できていません</strong><br>調べた公式情報では、粗大ごみを室内から運び出す支援を確認できていません。制度が存在しないと断定するものではありません。</p>'
    elif evidence == 'official_listing':
        banner = '<p class="gomi-evidence">公式案内をもとに整理しています。利用条件は窓口で確認してください。</p>'
    source_list = ''.join(
        f'<li id="source-{_e(source_keys[sid])}" data-source-id="{_e(source_keys[sid])}" data-checked="{_e(source_map[sid].get("checked") or "")}" data-updated="{_e(source_map[sid].get("source_updated") or "")}"><span>[{source_numbers[sid]}] {_e(source_map[sid].get("title") or sid)}</span>'
        + (f'<small>公式更新 {_e(source_map[sid]["source_updated"])} ・' if source_map[sid].get('source_updated') else '<small>')
        + (f' 確認 {_e(source_map[sid]["checked"])}' if source_map[sid].get('checked') else '')
        + f'</small> <a href="{_e(source_map[sid]["url"])}" target="_blank" rel="noopener">公式ページを開く</a></li>'
        for sid in used_ids)
    source_html = '<details class="gomi-route-sources" open><summary>この経路で参照した出典</summary><ol>' + source_list + '</ol></details>'
    questions = _questions_html(service.get('questions_for_office', []))
    if evidence == 'searched_not_found':
        # Keep contact and questions immediately usable; retain all other facts
        # and the search evidence in a native, keyboard-accessible disclosure.
        other_facts = ''.join(html for key, html in fact_html.items() if key != 'contact')
        body = (f'{banner}<dl class="gomi-facts">{fact_html["contact"]}</dl>{questions}'
                f'<details class="gomi-unconfirmed-details"><summary>未確認項目の詳細・調査根拠を開く</summary>'
                f'{notes}<dl class="gomi-facts">{other_facts}</dl>{source_html}</details>')
    else:
        body = f'{banner}{notes}<dl class="gomi-facts">{facts}</dl>{source_html}{questions}'
    return (f'<article class="gomi-route-card" id="route-{_e(service["id"])}" data-route="{_e(service["id"])}" data-kind="{_e(kind)}">'
            f'<header><p class="gomi-route-type">{_e(KIND_LABELS.get(kind,kind))}</p><h3>{_e(service.get("name","制度名未記載"))}</h3></header>'
            f'{body}'
            f'<a class="gomi-memo-shortcut" href="#gomi-memo" data-gomi-memo-route="route-{_e(service["id"])}">この方法の相談メモを作る →</a>'
            f'<p class="gomi-review-date">情報確認日：{_e(review_date)}</p>'
            f'</article>')


def _city_notice(city):
    if city.get('priority_notes'):
        items = ''.join(f'<li>{_e(note)}</li>' for note in city['priority_notes'])
        return f'<aside class="gomi-local-notice"><strong>この地域で先に確認したいこと</strong><ul>{items}</ul></aside>'
    by_kind = {s.get('kind'): s for s in city.get('services', [])}
    lines = []
    daily = by_kind.get('daily_support')
    if daily:
        scope = daily.get('fields', {}).get('waste_scope', {})
        if scope.get('value'):
            lines.append(f'{daily.get("name", "日常支援")}：{_value(scope["value"])}')
    regular = by_kind.get('regular_bulky')
    if regular:
        scope = regular.get('fields', {}).get('waste_scope', {})
        if scope.get('state') == 'explicit_exclusion' and scope.get('value'):
            lines.append('通常の粗大ごみ：' + _value(scope['value']))
    carry = by_kind.get('bulky_carry_support')
    if carry:
        f = carry.get('fields', {})
        state = f.get('indoor_carry', {}).get('state')
        if state == 'not_found':
            lines.append('室内からの搬出：今回確認した資料では公的な別制度を確認できていません。')
        elif f.get('indoor_carry', {}).get('value') is True:
            condition = f.get('eligibility', {}).get('value')
            lines.append('室内からの搬出支援：条件があります。' + (_value(condition) if condition else '対象条件は下の案内で確認してください。'))
    if not lines:
        return ''
    items = ''.join(f'<li>{_e(line)}</li>' for line in lines)
    return f'<aside class="gomi-local-notice"><strong>この地域で先に確認したいこと</strong><ul>{items}</ul></aside>'


def _city_main(city, sources, hub_rel, checked, human_reviewed):
    source_map = {x['id']: x for x in sources}
    services = city.get('services', [])
    by_kind = {kind: [s for s in services if s.get('kind') == kind] for kind in KIND_ORDER}
    anchors = ''.join(f'<a href="#{_e(kind)}">{_e(label)}</a>' for kind, label in KIND_LABELS.items())
    route_select = ''.join(f'<option value="route-{_e(s["id"])}">{_e(KIND_LABELS.get(s.get("kind"),s.get("kind")))}：{_e(s.get("name",""))}</option>' for s in services)
    sections = []
    for kind, label in KIND_LABELS.items():
        group = by_kind[kind]
        if not group:
            # The data may not cover this kind in a later municipality. Make the
            # gap explicit without implying that the service does not exist.
            sections.append(f'<section class="gomi-kind" id="{_e(kind)}"><h2>{_e(label)}</h2><p class="gomi-not-stated">この種類は今回の調査データに掲載していません。支援がないという意味ではありません。</p></section>')
        else:
            sections.append(f'<section class="gomi-kind" id="{_e(kind)}"><h2>{_e(label)}</h2>' + ''.join(_service_html(s,source_map,checked,human_reviewed) for s in group) + '</section>')
    question_html = _questions_html(city.get('common_questions_for_office', []), common=True)
    memo = f'''<section class="gomi-memo" id="gomi-memo" aria-labelledby="memo-title">
<p class="gomi-kicker">本人と家族で確認する</p><h2 id="memo-title">相談メモを作る</h2>
<p>選んだ経路の条件・費用・制限・窓口・出典をまとめます。入力内容はこの画面内だけで扱い、自動保存や送信はしません。</p>
<div class="gomi-memo-controls"><label>確認する経路<select data-gomi-route>{route_select}</select></label>
<label>ごみの種類・品目（任意）<input type="text" data-gomi-item placeholder="例：袋ごみ、たんす1点"></label>
<label>どこまで運べるか（任意）<select data-gomi-location><option>まだ分からない</option><option>指定された屋外まで出せる</option><option>敷地内・玄関先まで</option><option>室内から出せない</option><option>車で施設へ運べる</option></select></label>
<label>本人と確認したいこと（任意）<textarea data-gomi-notes rows="3" placeholder="例：通路の幅、階段、本人の在宅が必要か"></textarea></label></div>
<div class="gomi-memo-actions"><button type="button" data-gomi-copy>メモをコピー</button><button type="button" data-gomi-print data-print>相談メモを印刷</button><span data-gomi-status role="status" aria-live="polite"></span></div>
<textarea class="gomi-memo-preview" data-gomi-preview rows="14" readonly aria-label="作成した相談メモ">JavaScriptを使わなくても下の制度情報・出典を読めます。メモの自動作成とコピーにはJavaScriptが必要です。</textarea>
<pre class="gomi-print-memo" data-gomi-print-memo></pre>
<p class="gomi-note">このメモは利用決定・予約ではありません。対象条件や受付状況は自治体の窓口へ確認してください。健康・介護・住所など、本人を特定できる情報は入力しないでください。</p></section>'''
    return f'''<div class="gomi-page gomi-city" data-city="{_e(city['id'])}" data-human-reviewed="{str(bool(human_reviewed)).lower()}">
<div class="gomi-city-switch"><a href="{_e(hub_rel)}">ごみ出し支援の地域一覧へ</a></div>
<nav class="gomi-breadcrumb" aria-label="現在のページ"><a href="../index.html">トップ</a><span aria-hidden="true">›</span><a href="{_e(hub_rel)}">ごみ出し支援</a><span aria-hidden="true">›</span><span aria-current="page">{_e(city['name'])}</span></nav>
<p class="gomi-kicker">{_e(city['kana'])} ／ ごみ出しの相談先</p>
<h1>{_e(city['name'])}で、ごみを運び出せないとき</h1>
<p class="gomi-lead">まず、ごみの種類と「どこまで運べるか」を分けて確認します。袋ごみの日常支援と、家具などの粗大ごみの搬出支援は別の制度です。</p>
{_city_notice(city)}
<div class="gomi-research-note"><strong>{'調査用プレビュー' if city.get('publication_status') == 'research_only' else '掲載情報'}</strong><span>{'内容は' + _e(checked or '確認日未記載') + '時点の調査データです。' if city.get('publication_status') == 'research_only' else ''}「未記載」「今回未発見」は情報状態で、制度なし・無料・利用可能の確定を意味しません。制度の対象や受付状況は公式窓口で確認してください。{'項目は人手確認前です。' if not human_reviewed else '人手確認済みです。'}</span></div>
<section class="gomi-first"><h2>先に、ごみの種類と運べる場所を選ぶ</h2>
<div class="gomi-choice"><a href="#daily_support"><strong>袋ごみ・日常ごみ</strong><span>玄関先などで回収する支援</span></a><a href="#regular_bulky"><strong>家具・粗大ごみ</strong><span>指定場所への通常収集</span></a><a href="#bulky_carry_support"><strong>室内から出せない</strong><span>搬出支援の対象条件</span></a></div>
<label class="gomi-jump">確認したい経路へ移動<select data-gomi-jump><option value="">選択してください</option>{route_select}</select></label>
<p>玄関先まで運べることと、自治体の指定する屋外まで出せることは同じとは限りません。分からない場合は無理に運ばず、窓口へ回収場所を確認してください。</p></section>
<nav class="gomi-route-nav" aria-label="ごみの種類から選ぶ">{anchors}</nav>
{''.join(sections)}
{question_html}
{memo}
<section class="gomi-sources"><h2>出典と確認日</h2><p>項目ごとの根拠リンクと確認日を各制度の欄に記載しています。公式ページの更新日が確認できない場合は、調査データに記載の確認日だけを示しています。</p></section>
</div>'''


def _index_main(data):
    cards = []
    for city in data.get('cities', []):
        path = _slug(city)
        kinds = {s.get('kind') for s in city.get('services', [])}
        chip_labels = {'daily_support':'日常ごみを確認','bulky_carry_support':'室内搬出を確認','regular_bulky':'通常の粗大収集','self_dropoff':'自己搬入'}
        chips = ''.join(f'<span>{_e(chip_labels.get(k,KIND_LABELS[k]))}</span>' for k in KIND_ORDER if k in kinds)
        pref_name = city.get('pref_name') or city['id'].split(':',1)[0]
        search_value = f'{pref_name} {city["name"]} {city["kana"]}'
        cards.append(f'<li data-city-search="{_e(search_value)}"><a class="gomi-city-card" href="{_e(path)}"><strong>{_e(city["name"])}</strong><span>{_e(city["kana"])}</span><small class="gomi-pref-name">{_e(pref_name)}</small><div>{chips}</div><b>地域の案内を見る →</b></a></li>')
    reviewed = bool(data.get('human_reviewed'))
    checked = data.get('checked') or '確認日未記載'
    return f'''<div class="gomi-page gomi-index" id="prefectures" data-gomi-hub>
<p class="gomi-kicker">ごみを出す人にも、支える家族にも</p><h1>ごみを運び出せないときの地域の相談先</h1>
<div class="gomi-research-note"><strong>{'調査用プレビュー' if data.get('not_for_publication', True) else '掲載情報'}</strong><span>{'内容は' + _e(checked) + '時点の調査データです。' if data.get('not_for_publication', True) else ''}{'人手確認前です。' if not reviewed else '人手確認済みです。'}利用条件・受付状況は公式窓口にお確かめください。</span></div>
<section class="gomi-cities"><h2>掲載地域を選ぶ</h2><label class="gomi-hub-search">市町村名・かな・都道府県で探す<input type="search" data-gomi-city-search placeholder="例：神戸市、こうべ、兵庫県" autocomplete="off"></label><p data-gomi-city-count role="status">{len(cards)}地域を掲載しています。</p><ul data-gomi-city-list>{''.join(cards)}</ul><p class="gomi-no-results" data-gomi-no-results hidden>一致する地域がありません。自治体名や都道府県名を変えてください。</p></section>
<p class="gomi-lead">袋ごみの日常支援と、家具などの粗大ごみの搬出支援を地域ごとに確認できます。地域を選ぶと、対象条件と相談先を見られます。</p>
<section class="gomi-first"><h2>「日常ごみ」と「家具」は別に確認</h2><div class="gomi-split"><div><h3>日常の袋ごみ</h3><p>玄関先や敷地内で回収する支援があります。対象世帯や家族の協力条件を確認します。</p></div><div><h3>家具などの粗大ごみ</h3><p>通常収集は指定場所まで自分で運ぶ場合があります。室内搬出支援や自己搬入とは別の方法です。</p></div></div></section>
<p class="gomi-note">この一覧にない地域も、支援制度がないとは限りません。自治体のごみ担当窓口へご相談ください。</p></div>'''


def _finish(html, relative, title, description, draft, is_index=False, draft_note=''):
    import build as b
    from site_header import apply_site_header
    base = '../' if '/' in relative else ''
    soup = BeautifulSoup(b.shell(title=title, description=description, path=relative,
                                 main=html, draft=draft,
                                 draft_note=draft_note or ('ごみ出し支援の調査用プレビューです。' if draft else ''),
                                 base=base, page_class='gomi-shell',
                                 styles=f'<link rel="stylesheet" href="{base}assets/warm-shared.css"><link rel="stylesheet" href="{base}assets/gomi-support.css">'), 'html.parser')
    if draft:
        soup.select_one('.draft').string = '公開前の確認用｜掲載情報は人手確認前です。'
    if is_index:
        notice = soup.select_one('.gomi-research-note')
        if notice:
            notice.decompose()
    else:
        # Put the four routes within reach before the longer local conditions.
        route_nav = soup.select_one('.gomi-route-nav')
        lead = soup.select_one('.gomi-lead')
        if route_nav and lead:
            lead.insert_after(route_nav.extract())
        duplicate_picker = soup.select_one('.gomi-first')
        if duplicate_picker:
            duplicate_picker.decompose()
        repeated_preview = soup.select_one('.gomi-research-note')
        if repeated_preview:
            repeated_preview.clear()
            repeated_preview.append('「記載なし・未発見」は制度なしや無料を意味しません。回収場所と対象条件を公式窓口で確認してください。')
    soup.body['class'] = list(set(soup.body.get('class', []) + ['gomi-support-body']))
    soup.html['class'] = list(set(soup.html.get('class', []) + ['gomi-document']))
    # Use the shared municipality-first header adapter with this page's controls.
    topbar = soup.select_one('.topbar')
    if topbar:
        topbar.name = 'header'
        topbar['class'] = ['mast']
        nav = topbar.select_one('.site-nav')
        if nav:
            nav.decompose()
        size = topbar.select_one('.sizer')
        if size:
            size['class'] = ['size']
            for button in size.select('button'):
                button['data-size'] = button.get('data-size-btn', 'normal')
        if not is_index:
            switch = soup.new_tag('div', attrs={'class':'city-switch'})
            link = soup.new_tag('a', href=f'{base}gomi-support.html')
            link.string = 'ごみ出し支援の地域一覧'
            switch.append(link)
            soup.main.insert(0, switch)
    # Share the national pages' same-tab font setting, not legacy localStorage.
    for script in list(soup.find_all('script')):
        if 'jk-size' in script.get_text() or 'querySelectorAll("[data-size-btn]")' in script.get_text():
            script.decompose()
    # Remove site-wide tracking bootstrap: this preview must not emit analytics.
    if draft:
        for script in list(soup.find_all('script')):
            if 'googletagmanager' in str(script) or 'gtag(' in script.get_text():
                script.decompose()
    for node in list(soup.select('link[href^="https://fonts.googleapis.com"], link[href^="https://fonts.gstatic.com"]')):
        node.decompose()
    # The theme uses the warm shared palette instead of the legacy global sheet.
    for link in list(soup.select('link[rel="stylesheet"]')):
        if link.get('href', '').split('?')[0].endswith('/site.css') or link.get('href', '').split('?')[0] == f'{base}site.css':
            link.decompose()
    apply_site_header(soup, base=base, home=False)
    region = soup.select_one('.site-region-link')
    if region:
        region['href'] = '#prefectures' if is_index else f'{base}gomi-support.html#prefectures'
    # Local script only: no storage, requests or telemetry.
    script = soup.new_tag('script', src=f'{base}assets/gomi-support.js', defer=True)
    soup.body.append(script)
    return str(soup)


def generate_pages(data, draft=True):
    """Return the five (hub + four city) HTML documents as relative-path keys."""
    if not draft:
        import build as b
        from validate_gomi import validate
        errors = validate(data, root=b.ROOT, publication=True)
        if errors:
            raise ValueError('Waste support publication validation failed: ' + '; '.join(errors))
    pages = {}
    sources = data.get('sources', [])
    index_path = 'gomi-support.html'
    pages[index_path] = _finish(_index_main(data), index_path,
                                'ごみ出し支援の相談先を地域から探す｜じもとくらべ',
                                '日常のごみ出し支援と粗大ごみの搬出方法を自治体ごとに確認できます。',
                                draft=draft, is_index=True,
                                draft_note=f'ごみ出し支援の調査用プレビューです。調査基準日：{data.get("checked") or "未記載"}。')
    for city in data.get('cities', []):
        relative = _slug(city)
        pages[relative] = _finish(_city_main(city, sources, '../gomi-support.html', data.get('checked'), bool(data.get('human_reviewed'))), relative,
                                  f'{city["name"]}でごみを運び出せないとき｜じもとくらべ',
                                  f'{city["name"]}の日常ごみ支援、粗大ごみ収集、室内搬出、自己搬入の条件と相談先。',
                                  draft=draft,
                                  draft_note=f'{city["name"]}のごみ出し支援の調査用情報です。調査基準日：{data.get("checked") or "未記載"}。')
    return pages
