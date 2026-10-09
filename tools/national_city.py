"""Render nationwide municipal support pages from the repository records.

Source records are read only. Conditions, cautions and confirmation dates are
retained without inferring entitlement or calculating combined benefit totals.
"""
from pathlib import Path
from urllib.parse import urljoin
import argparse
import copy
import html
import json
import re
import unicodedata
from bs4 import BeautifulSoup

BASE = 'https://jimotokurabe.jp/'
HAND = {('hyogo', 'kobe'), ('kanagawa', 'yokohama'), ('kagoshima', 'kagoshima')}
LABELS = {
    'what':'内容', 'age':'対象・年齢', 'amt':'支援内容', 'dl':'申請期限',
    'apply':'申請・問い合わせ', 'how':'申請方法', 'henno_link':'免許返納との関係',
    'note':'補足・注意', 'notes':'補足・注意', 'flag':'確認が必要な点',
    'name':'制度・窓口の名前', 'summary':'概要', 'eligibility':'対象・条件',
    'benefit':'支援内容', 'fare':'本人負担・運賃', 'routes':'利用できる交通',
    'sources':'公式出典', 'url':'公式案内', 'source':'公式案内', 'src':'出典名',
    'upd':'出典の更新日', 'updated':'出典の更新日', 'source_updated':'出典の更新日',
    'date':'出典の日付', 'checked':'内容の確認日', 'label':'出典名',
    'body':'案内', 'title':'案内名', 'link_url':'公式一覧', 'link_label':'一覧の案内',
    'src_url':'公式出典', 'src_label':'出典名', 'list_url':'特典の一覧',
    'who':'対象', 'bus':'バスの割引', 'taxi':'タクシーの割引', 'as_of':'一覧の基準日',
    'lead':'案内', 'facts':'条件・申請の要点', 'cautions':'手続き前の注意',
    'return_places':'免許返納の窓口', 'return_note':'返納窓口について',
    'receive_note':'返納後に受け取るもの', 'step2_title':'運転経歴証明書の手続き',
    'step2_lead':'運転経歴証明書について', 'stations':'市町村内の警察署',
    'contacts':'問い合わせ', 'local_discounts':'地域の割引', 'extra':'補足の案内',
    'extra_title':'補足の案内名', 'extra_src':'補足の出典', 'extras':'地域独自の案内',
    'use':'特典の利用方法', 'items':'案内', 'links':'関連する公式案内',
    'summary_links':'申請・確認の案内', 'heading':'案内名', 'write':'申請方法',
    'attach_label':'必要書類の項目', 'attach':'必要書類', 'address_label':'提出先の項目',
    'address':'申請先・宛先', 'office':'担当窓口', 'tel':'電話', 'proxy':'代理申請',
    'ways':'申請方法', 'checklist':'持ち物・準備するもの', 'more':'期限・条件の詳しい案内',
    'choice_note':'選択する際の注意', 'deadline':'期限の基準', 'form_url':'申請用紙',
    'form_label':'申請用紙の案内', 'where':'場所', 'hours':'受付時間',
    'fee':'返納の費用', 'fees':'手数料', 'center_hours':'免許センターの受付',
    'station_hours':'警察署の受付', 'stations_url':'警察署の一覧', 'mail':'郵送の手続き',
    'centers':'免許センター', 'need':'必要なもの', 'within':'申請できる期間',
    'quick_scope':'掲載する地域・交通の範囲', 'scope':'掲載範囲', 'hint':'案内',
    'rides':'交通手段', 'supports':'運賃支援', 'service_area':'利用地域',
    'booking':'予約・申し込み', 'operating_days':'運行日', 'check':'利用前に確認すること',
    'tags':'利用のポイント', 'value':'確認した内容', 'evidence':'公式案内の抜き書き',
    'unresolved':'まだ確認できていないこと', 'guide_details':'利用条件の補足',
    'guide_relation_note':'他の支援との関係', 'guide_heading':'支援名',
    'more_sources':'追加の出典', 'transport':'交通の案内', 'link':'確認先',
    'photo':'写真について', 'photo_size':'写真の大きさ', 'issue':'受け取り',
    'documents':'必要書類', 'period':'対象期間', 'notice':'注意',
    'href':'関連する案内', 'hennou':'免許返納の手続き',
    'keireki':'運転経歴証明書の手続き', 'keireki_lead':'運転経歴証明書について', 'checklist':'準備するもの',
}
META = {'slug','n','y','r','k','status','id','pref','municipality','city','group',
        'level','focus','kind','age_min','current','draft','reviewed','safety_accepted',
        'key','fetch_status','field','topic','purposes','search_title','short','description',
        'link_label','guide_mobility','guide_relation','guide_anchor','henno_earlier',
        'date_label','offset','days','months','years','mode','format','default'}

def e(v):
    return html.escape(str(v), quote=True)

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def link(url, label, cls=''):
    if not url:
        return ''
    url = str(url)
    if not url.startswith(('https://','http://','tel:','#')):
        url = urljoin(BASE, url)
    return f'<a class="{cls}" href="{e(url)}">{e(label)}</a>'

def text_value(value):
    s = str(value)
    if s.startswith(('https://','http://','tel:')) and not re.search(r'\s', s):
        return link(s, '公式案内を開く ↗')
    # Keep the original text intact; exact URLs in records receive links above.
    return e(s).replace('\n', '<br>')

def date_line(record, inherited):
    return '<p class="dates">内容の確認日：'+e(record.get('checked') or inherited or '未記録')+'</p>'

def recursive(data, checked='', depth=0, skip=()):
    """Readable record fields. Unknown fields are retained in a supplemental label.

    Source-local checked dates take priority over item and file dates.
    """
    if data is None or data == '' or data == [] or data == {}:
        return ''
    if isinstance(data, bool):
        return ''
    if isinstance(data, dict):
        local = data.get('checked') or checked
        rows=[]
        for key, value in data.items():
            if key in META or key in skip or value is None or value == '' or value == [] or value == {}:
                continue
            if key == 'checked':
                continue
            label=LABELS.get(key, '補足情報')
            inner=link(value, '関連する案内を開く ↗') if key=='href' else recursive(value, local, depth+1)
            if inner:
                important=' class="important"' if key in ('note','notes','flag','cautions','check','unresolved') else ''
                rows.append(f'<div{important}><dt>{e(label)}</dt><dd>{inner}</dd></div>')
        result='<dl class="facts record-fields">'+''.join(rows)+'</dl>' if rows else ''
        # Every official source gets its effective confirmation date, even when it
        # inherits that date. Page/source updated date remains separate.
        if data.get('url') or data.get('source') or data.get('checked'):
            result += date_line(data, checked)
        return result
    if isinstance(data, list):
        # Guide action rows carry title, explanation, fragment, link label.
        if len(data) == 4 and all(isinstance(x, str) for x in data) and data[2].startswith('#'):
            return '<strong>'+e(data[0])+'</strong><p>'+text_value(data[1])+'</p>'+link(data[2],data[3])
        # Named pairs in guide facts, fees, application ways etc. stay readable.
        if data and all(isinstance(x, list) and len(x)==2 and isinstance(x[0],str) for x in data):
            return '<dl class="facts">'+''.join(
                '<div><dt>'+('ページ内の案内' if a.startswith('#') else '公式案内')+'</dt><dd>'+link(a,b)+'</dd></div>'
                if a.startswith(('https://','http://','tel:','#')) and isinstance(b,str) and not re.search(r'\s',a)
                else '<div><dt>'+e(a)+'</dt><dd>'+recursive(b,checked,depth+1)+'</dd></div>'
                for a,b in data)+'</dl>'
        return '<ul class="record-list">'+''.join('<li>'+recursive(x,checked,depth+1)+'</li>' for x in unique(data))+'</ul>'
    return text_value(data)

def unique(items):
    seen=set();result=[]
    for item in items:
        identity=json.dumps(item,sort_keys=True,ensure_ascii=False)
        if identity not in seen:
            seen.add(identity);result.append(item)
    return result

def section(anchor, title, body):
    alias = {'support':'bus','procedure':'step-3'}.get(anchor)
    prefix = '<span id="'+alias+'" class="legacy-anchor"></span>' if alias else ''
    if anchor == 'procedure': prefix += '<span id="steps-h" class="legacy-anchor"></span>'
    return f'<section class="block" id="{e(anchor)}">{prefix}<h2>{e(title)}</h2>{body}</section>'

def details(title, body):
    return f'<details><summary>{e(title)}</summary>{body}</details>'

def card(title, body, anchor=''):
    return f'<article class="subprogram"'+(f' id="{e(anchor)}"' if anchor else '')+f'><h3>{e(title)}</h3>{body}</article>'

def normalize(s):
    return re.sub(r'[\W_]+','',unicodedata.normalize('NFKC', str(s))).lower()

def aligned(return_record, program):
    """Conservative display grouping, never record deletion or inferred merging.

    Same municipal record, exact official URL, henno classification AND an
    explicit matching benefit string are all required. URL alone is insufficient.
    """
    if program.get('kind') != 'henno' or not return_record.get('url'):
        return False
    if return_record['url'] not in [s.get('url') for s in program.get('sources',[])]:
        return False
    a,b=normalize(return_record.get('amt','')),normalize(program.get('benefit',''))
    return bool(min(len(a),len(b))>=5 and (a in b or b in a))

def bus_program(p, checked):
    state=p.get('current')
    caution = '<p class="important">現在の適用条件を窓口で確認する必要があります。利用・申請前に公式案内をご確認ください。</p>' if state=='needs_confirmation' else ''
    relation='<p class="badge warn">免許返納に関連する支援</p>' if p.get('kind')=='henno' else '<p class="mini-note">免許返納との関係は、以下の対象・条件で確認してください。</p>'
    return relation+caution+recursive(p,checked)+date_line(p,checked)

def accepted_updates(record):
    return [u for u in record.get('updates',[]) if isinstance(u,dict)
            and u.get('reviewed') is True and u.get('safety_accepted') is True
            and u.get('value') and u.get('source') and u.get('evidence')]

def gather(root):
    prefs={};bus={};taxi={}
    for path in sorted((root/'data').glob('*-menkyo-henno.json')):
        d=load(path);pid=d['pref']['id'];prefs[pid]=d
        bp=root/'data'/f'{pid}-bus.json';tp=root/'data'/f'{pid}-taxi.json'
        if bp.exists():bus[pid]=load(bp)
        if tp.exists():taxi[pid]=load(tp)
    supplemental=load(root/'data/municipality-supplements.json')
    mobility={}
    md=load(root/'data/municipal-mobility.json')
    for m in md['cities']:
        mobility.setdefault((m['pref'],m['municipality']),[]).append({'record':m,'checked':m.get('checked') or md['checked'],'coverage':{'scope':m['scope'],'level':m['level'],'page':f"{m['pref']}-mobility/{m['municipality']}.html"}})
    east=load(root/'data/east-harima-mobility.json');byid={m['id']:m for m in east['cities']}
    coverage=load(root/'data/mobility-coverage.json')
    for c in coverage['entries']:
        m=byid[c['city']]
        mobility.setdefault((c['pref'],c['municipality']),[]).append({'record':m,'checked':m.get('checked') or east['checked'],'coverage':c,'coverage_checked':c.get('checked') or coverage['checked']})
    return prefs,bus,taxi,supplemental,mobility

def adopted(pid,city,d,bus,taxi,supp,mobility):
    b=bus.get(pid);bc=next((c for c in b['cities'] if c['slug']==city['slug']),None) if b else None
    t=taxi.get(pid,{});tc=t.get('cities',{}).get(city['slug'])
    s=supp['records'].get(pid+':'+city['slug'],{})
    return {'municipality':{'key':pid+':'+city['slug'],'name':city['n']},
            'return':city,'return_checked':city.get('checked') or d['checked'],
            'guide_checked':city.get('guide',{}).get('checked') or city.get('checked') or d['checked'],
            'bus':bc,'bus_checked':bc.get('checked') or b.get('checked') if bc else None,
            'bus_common':b.get('common') if b else None,
            'taxi':tc,'taxi_checked':tc.get('checked') or t.get('checked') if tc else None,
            'statewide':d['pref'].get('statewide',{}),'common':d.get('common',{}),
            'common_checked':d.get('common',{}).get('checked') or d['checked'],
            'accepted_supplements':accepted_updates(s),'supplement_checked':s.get('checked'),
            'supplement_unresolved':s.get('unresolved',[]) if accepted_updates(s) else [],
            'mobility':mobility.get((pid,city['slug']),[])}

def supplements_body(a):
    if not a['accepted_supplements']:
        return ''
    body='<p class="mini-note">掲載済みの制度を補足する案内です。同じ支援の説明を、追加の給付として合計しないでください。</p>'
    for u in unique(a['accepted_supplements']):
        body+=card('確認済みの補足',recursive(u,a['supplement_checked'],skip=('evidence',))+date_line(u,a['supplement_checked'])+details('公式案内の原文で確認',recursive(u['evidence'],a['supplement_checked'])))
    if a['supplement_unresolved']:
        body+='<h3>まだ確認できていないこと</h3>'+recursive(a['supplement_unresolved'],a['supplement_checked'])
    return section('confirmed','公式情報で確認した補足',body)

def guide_body(g, common, checked, common_checked):
    if not g:
        return '<p>この市町村の独自の手順案内は未掲載です。返納の受付・必要書類は、県警の案内と窓口でご確認ください。</p>'+details('都道府県の返納・経歴証明書の手続き',recursive({k:v for k,v in common.items() if k not in ('tokuten','checked')},common_checked))
    primary={k:v for k,v in g.items() if k not in ('sources','stations','summary_links','links','mobility','title','description','facts','local_discounts','extras','extra','extra_title','extra_src')}
    body='<p>免許の返納と、支援制度の申請は別の手続きです。まず対象・期限を確認し、受付窓口で必要書類を確かめてください。</p>'+date_line(g,checked)+recursive(primary,checked)
    if g.get('stations'):
        body+=details('市町村内の警察署・電話番号',recursive(g['stations'],checked))
    body+=recursive({k:v for k,v in g.items() if k in ('sources','summary_links','links','mobility')},checked)
    extra={k:v for k,v in g.items() if k in ('extra','extras','extra_title','extra_src')}
    if extra:body+='<span id="extra" class="legacy-anchor"></span><h3>市町村の手順案内にある関連制度・補足</h3>'+recursive(extra,checked)
    body+=details('都道府県の返納・経歴証明書の共通手続き',recursive({k:v for k,v in common.items() if k not in ('tokuten','checked')},common_checked))
    return body

def mobility_body(a):
    if not a['mobility']:
        return '<div class="unknown"><p>個別の交通手段・運行・予約の詳しい案内は、このページでは未掲載です。掲載済みの支援の利用路線は、各制度の条件でご確認ください。</p></div>'
    body=''
    for item in a['mobility']:
        m=item['record'];cv=item['coverage'];checked=item['checked']
        body+='<div class="notice"><strong>掲載範囲：'+e(cv.get('scope',m.get('scope',m['name'])))+'</strong><p>'+e(m.get('quick_scope',''))+'</p>'
        if cv.get('level')=='partial':
            body+='<p>地区や制度を限定した情報です。市町村全域・すべての交通手段を網羅した案内ではありません。</p>'
        body+='</div>'+date_line(m,checked)
        if item.get('coverage_checked'):
            body+='<p class="dates">掲載範囲の対応表の確認日：'+e(item['coverage_checked'])+'</p>'
        for category,title in [('rides','交通手段'),('supports','地域交通に関連する運賃支援')]:
            if m.get(category):
                body+='<h3>'+title+'</h3>'
                for r in unique(m[category]):body+=card(r['name'],recursive(r,checked)+date_line(r,checked))
        if not m.get('rides'):body+='<p>この案内は運賃支援のみです。個別の交通手段・運行・予約は未掲載です。</p>'
        body+=link(cv.get('page'),m['name']+'の交通案内を開く ↗','primary')
    return body

def short(v):
    v=str(v or '詳細で対象・条件を確認')
    return v if len(v)<135 else v[:132]+'…'

def city_js(js):
    """Keep the prototype's interactions and share font choice with navigation."""
    if 'jk-national-size' in js:
        return js
    js=js.replace("function font(enlarge){", "function font(enlarge){try{sessionStorage.setItem('jk-national-size',enlarge?'large':'normal');}catch(error){}")
    js=js.replace("normal.addEventListener('click'", "try{font(sessionStorage.getItem('jk-national-size')==='large');}catch(error){}normal.addEventListener('click'", 1)
    return js

def overview(a):
    c=a['return'];b=a['bus'];t=a['taxi'];m=a['mobility']
    return_text='掲載調査では未確認' if c.get('k')=='notfound' else c.get('amt') or c.get('what')
    bus_text='バス支援の詳細は未掲載' if b is None else ('掲載調査では未確認' if b.get('status')=='notfound' else b.get('summary') or '詳細で条件を確認')
    taxi_text='掲載調査では未確認' if t and t.get('k')=='notfound' else (t.get('amt') or t.get('what')) if t else '詳細は未掲載'
    ride_text='対象地区・予約・運賃を確認' if m else '個別の運行・予約は未掲載'
    programs=b.get('programs',[]) if b else []
    bus_condition=programs[0].get('eligibility','対象・条件を詳細で確認') if len(programs)==1 else '制度ごとに対象・条件が異なります' if len(programs)>1 else '掲載状況を詳細で確認'
    return_condition=c.get('age') if c.get('age') and c['age']!='記載なし' else '返納・経歴証明書の条件を確認'
    taxi_condition=t.get('age') if t and t.get('age') and t['age']!='記載なし' else '対象者・事業者・使い方を確認'
    ride_condition='／'.join(x['coverage']['scope'] for x in m) if m else '掲載範囲・行き先を確認'
    rows=[('benefit','免許返納の特典',short(return_condition),return_text),('support','バス助成・敬老パス',short(bus_condition),bus_text),('taxi','タクシー支援',short(taxi_condition),taxi_text),('rides','通院・買い物の足',short(ride_condition),ride_text)]
    return '<section class="intro" aria-labelledby="overview-title"><div class="section-head"><h2 id="overview-title">まずは、支援の見取り図</h2><p>項目を選ぶと、条件・申請先へ進みます。</p></div><ul class="overview">'+''.join(f'<li><a href="#{i}"><strong>{e(label)}</strong><span class="condition">{e(condition)}</span><span class="value">{e(short(value))}<small>掲載情報に基づく案内</small></span><span class="arrow" aria-hidden="true">↓</span></a></li>' for i,label,condition,value in rows)+'</ul></section>'

def render_generic(pid,c,d,a,prototype):
    checked=a['return_checked'];g=c.get('guide',{});b=a['bus'];t=a['taxi'];common=a['common']
    grouped=[p for p in unique(b.get('programs',[])) if aligned(c,p)] if b else []
    benefit='<p class="mini-note">市町村独自の支援と、都道府県共通の特典を分けて確認します。</p>'
    if c.get('k')=='notfound':
        benefit+='<div class="unknown"><h3>市町村独自の返納特典は、掲載調査では未確認</h3><p>制度がないと断定するものではありません。下の記録・県共通の支援と、公式窓口でご確認ください。</p></div>'
    if c.get('k')=='end':benefit+='<p class="important">受付を終了した特典の案内を含みます。終了・期限の案内をご確認ください。</p>'
    municipal=recursive(c,checked,skip=('guide',))+date_line(c,checked)
    if g.get('facts'):municipal+='<h4>市町村の手順案内に記載された条件</h4>'+recursive(g['facts'],g.get('checked') or checked)
    if g.get('local_discounts'):municipal+='<h4>手順案内に記載された地域の割引</h4>'+recursive(g['local_discounts'],g.get('checked') or checked)
    for n,p in enumerate(grouped):
        municipal+='<h4>同じ支援のバスに関する補足</h4><p class="mini-note">同じ制度の支援内容をまとめています。追加の給付ではありません。対象条件と確認日をご確認ください。</p>'+bus_program(p,a['bus_checked'])
    if t and t.get('guide_relation')=='same':
        municipal+='<h4>同じ支援のタクシーに関する補足</h4><p class="mini-note">返納特典と同じ支援の案内です。追加の給付ではありません。</p>'+recursive(t,a['taxi_checked'])+date_line(t,a['taxi_checked'])
    benefit+=card('市町村の返納支援',municipal,'return-record')
    if a['statewide'] or common.get('tokuten'):
        benefit+=card(d['pref']['name']+'で共通の返納支援', '<p class="mini-note">利用できる店舗・事業者と対象条件を確認してください。市町村独自の給付とは別の案内です。</p>'+recursive(a['statewide'],a['common_checked'])+recursive(common.get('tokuten',{}),a['common_checked'])+date_line({},a['common_checked']), 'statewide')
    busbody=''
    if not b:busbody='<div class="unknown"><h3>バス支援の詳細は未掲載</h3><p>この道県の自治体別バス調査データは未収録です。支援制度の有無を示すものではありません。</p></div>'
    else:
        if b.get('status')=='notfound':busbody+='<div class="unknown"><h3>掲載調査では未確認</h3><p>自治体独自のバス助成がないと断定するものではありません。県共通の特典や交通事業者の制度は、それぞれの条件をご確認ください。</p></div>'
        elif b.get('status')=='unknown':busbody+='<div class="notice"><strong>詳細は確認が必要です</strong><p>掲載情報だけでは対象・条件を確定できません。公式案内・窓口で確認してください。</p></div>'
        elif b.get('status')=='ended':busbody+='<p class="important">終了した支援の案内を含みます。現在の受付・利用可否は公式案内で確認してください。</p>'
        busbody+=recursive(b,a['bus_checked'],skip=('programs',))+date_line(b,a['bus_checked'])
        for p in unique(b.get('programs',[])):
            if p in grouped:busbody+='<p class="cross">'+link('#return-record',p['name']+'：免許返納の欄で、同じ支援の条件を確認 ↑')+'</p>'
            else:
                related=''
                if p.get('kind')=='henno' and c.get('k')!='notfound':related='<p class="mini-note">免許返納の支援と関連する可能性があります。別々の給付として数えず、対象制度・併用条件を窓口で確認してください。</p>'
                busbody+=card(p['name'],related+bus_program(p,a['bus_checked']))
        if a['bus_common']:busbody+=details(d['pref']['name']+'の共通のバス関連案内',recursive(a['bus_common'],a['bus_checked']))
    if not b:
        busbody+='<p class="mini-note">返納に伴う交通の割引は、'+link('#benefit','免許返納の特典')+'もご確認ください。'
        if a['accepted_supplements']:
            busbody+=' 市町村について確認できた補足は、'+link('#confirmed','公式情報の補足')+'で読めます。'
        busbody+='</p>'
    taxibody=recursive(t,a['taxi_checked'])+date_line(t,a['taxi_checked']) if t else '<p>タクシー支援の詳細は未掲載です。</p>'
    if t and t.get('k')=='notfound':taxibody='<div class="unknown"><h3>掲載調査では未確認</h3><p>すべての助成制度がないと断定するものではありません。</p></div>'+taxibody
    if t and t.get('guide_relation')=='same':taxibody='<p class="cross">返納特典と同じ支援の案内です。'+link('#return-record','同じ支援の対象・条件・申請先を確認 ↑')+'。タクシー支援の内容と出典も、同じ欄で確認できます。</p>'
    body=section('benefit','免許返納の特典',benefit)+section('support','バス助成・敬老パス',busbody)+section('taxi','タクシー支援',taxibody)+section('rides','通院・買い物に使う交通',mobility_body(a))+supplements_body(a)+section('procedure','返納の手順・持ち物',guide_body(g,common,a['guide_checked'],a['common_checked']))+str(prototype.select_one('#family'))
    related='<p>出典の更新日と内容の確認日は、それぞれの制度・手順の欄に表示しています。公式ページ・窓口で最新の条件をご確認ください。</p>'
    related+='<ul class="sources">'+''.join('<li>'+link(BASE+f'{pid}-{topic}.html#'+c['slug'],label+' ↗')+'</li>' for topic,label in [('menkyo-henno','県の返納案内'),('taxi','県のタクシー案内')])+('</ul>')
    if b:related+=link(BASE+pid+'-bus.html#'+c['slug'],'県のバス調査の記録 ↗')
    body+=section('related','関連する案内・出典',related)
    mast=copy.copy(prototype.select_one('.mast'));mast.select_one('.brand')['href']='../index.html'
    side='<nav class="side" aria-label="このページの案内"><p>'+e(c['n'])+'の移動と支援</p>'+''.join(link('#'+i,label) for i,label in [('benefit','免許返納の特典'),('support','バス助成・敬老パス'),('taxi','タクシー支援'),('rides','通院・買い物の足'),('procedure','返納の手順・持ち物'),('family','家族と一緒に確認'),('related','関連する案内・出典')])+'</nav>'
    nav=f'<nav class="city-switch" aria-label="地域を選び直す"><a href="../index.html">トップから探す</a><a href="../{pid}-menkyo-henno.html">{e(d["pref"]["name"])}の市町村を選ぶ</a></nav>'
    dates='<p class="dates">返納情報：'+e(a['return_checked'])+'確認'+(' ／ バス情報：'+e(a['bus_checked'])+'確認' if b else '')+(' ／ タクシー情報：'+e(a['taxi_checked'])+'確認' if t else '')+'<br>各出典・手順・補足の確認日は、個別の欄で確認できます。</p>'
    return f'<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><meta name="referrer" content="no-referrer"><title>{e(c["n"])}の移動と支援｜じもとくらべ・未公開プレビュー</title><link rel="stylesheet" href="../assets/national-city.css"></head><body><a class="skip" href="#main">本文へ移動</a><div class="draftbar">画面構成の確認用・未公開 ／ 既存の掲載記録を使用。今回、制度の追加調査は行っていません</div><div class="wrap">{mast}{nav}<nav class="crumb" aria-label="現在の場所"><a href="../index.html">トップ</a><span>›</span><a href="../{pid}-menkyo-henno.html">{e(d["pref"]["name"])}</a><span>›</span><span aria-current="page">{e(c["n"])}</span></nav><main id="main"><header class="hero"><div><p class="eyebrow">免許を返したあとの暮らしに。</p><h1>{e(c["n"])}の<br>移動と支援</h1><p>返納した方も、これから考える方も。<br>対象条件・費用・申請先をまとめて確認できます。</p></div></header>{overview(a)}{dates}<div class="layout">{side}<div class="content">{body}</div></div></main>{prototype.footer}</div><script src="../assets/national-city.js"></script></body></html>'

def leaves(data,path=()):
    if isinstance(data,dict):
        for k,v in data.items():
            if k not in META and k != 'guide':yield from leaves(v,path+(k,))
    elif isinstance(data,list):
        for v in data:yield from leaves(v,path)
    elif isinstance(data,str) and data and data != '記載なし':
        yield path,data

def render_hand(source,pid,c,d,a):
    soup=BeautifulSoup(source.read_text(encoding='utf-8'),'html.parser')
    # Internal comparison dumps are not reader-facing guidance. Missing facts
    # are rendered below from the current source records instead.
    for dump in soup.find_all('pre'):
        if dump.get_text(strip=True).startswith('{'):
            container = dump.find_parent('details')
            (container if container is not None else dump).decompose()
    for x in soup.select('.city-switch'):
        x.clear();x.append(BeautifulSoup(f'<a href="../index.html">トップから探す</a><a href="../{pid}-menkyo-henno.html">{e(d["pref"]["name"])}の市町村を選ぶ</a>','html.parser'))
    for x in soup.select('.hero-tools'):
        x.clear();x.append(BeautifulSoup(f'<a href="../{pid}-menkyo-henno.html">{e(d["pref"]["name"])}の市町村を選ぶ →</a>','html.parser'))
    for x in soup.select('.brand'):x['href']='../index.html'
    # Only navigation changes above; missing original record information is
    # retained below as clearly labelled comparison material, never a new benefit.
    visible=copy.copy(soup)
    for x in visible.select('script,style'):x.decompose()
    present=normalize(visible.get_text(' ',strip=True));hrefs={x.get('href') for x in visible.select('a[href]')}
    candidates=[('返納支援',a['return'],a['return_checked']),('バス支援',a['bus'],a['bus_checked']),('タクシー支援',a['taxi'],a['taxi_checked']),('都道府県共通の案内',a['statewide'],a['common_checked']),('県内共通のバス案内',a['bus_common'],a['bus_checked']),('返納・証明書の共通手続き',a['common'],a['common_checked'])]
    supplement=''
    for title,record,checked in candidates:
        missing=[]
        for path,value in leaves(record):
            if value in hrefs or normalize(value) in present:continue
            missing.append({'label':LABELS.get(path[-1],'補足情報') if path else '内容','value':value})
        if missing:
            fields='<dl class="facts">'+''.join('<div><dt>'+e(v['label'])+'</dt><dd>'+text_value(v['value'])+'</dd></div>' for v in unique(missing))+'</dl>'
            supplement+=details(title+'の補足・出典','<p class="mini-note">上の支援と同じ制度についての補足情報です。追加の給付ではありません。</p>'+fields+date_line({},checked))
    supplement+=supplements_body(a)
    # Supplemental fields retain source statements absent from the custom layout.
    if supplement:
        target=soup.select_one('#related') or soup.select_one('.content') or soup.main
        target.append(BeautifulSoup('<div class="archive-wrap"><h3>補足情報・出典と確認日</h3>'+supplement+'</div>','html.parser'))
    for record_tag in soup.select('#preserved-records'):
        record_tag.decompose()
    style=soup.new_tag('link',rel='stylesheet',href='../assets/national-city.css');soup.head.append(style)
    for meta in soup.select('meta[name="robots"]'):meta['content']='noindex,nofollow'
    # Templates supply only the local interactions; site scripts are added later.
    for s in soup.select('script[src]'):
        if s['src'].startswith(('http:','https:','//')):s.decompose()
    for script in soup.find_all('script'):
        if script.get('type')!='application/json' and script.string:
            script.string=city_js(script.string)
    return str(soup)

def build_all(root:Path,out:Path,draft:bool=False)->dict:
    from seo_content import make_city_content
    from warm_city import apply_warm_city
    import shutil
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    reference=Path(__file__).resolve().parent/'templates'/'national'
    kobe=BeautifulSoup((reference/'hyogo-kobe.txt').read_text(encoding='utf-8'),'html.parser')
    base_css=kobe.style.string
    css_add='''\n/* Nationwide city page extensions: records are readable at 320px. */
button,.city-switch a,.crumb a,footer a{min-height:48px}.sources a,.facts a,.record-list a,.cross a{display:inline-flex;align-items:center;min-height:48px;max-width:100%;overflow-wrap:anywhere}.side a{min-height:48px}.hero-tools a{display:inline-flex;align-items:center;min-height:48px}p,li,dd{overflow-wrap:anywhere}.record-fields .record-fields{margin:0}.record-fields .record-fields>div{display:block;padding:10px 0}.record-fields .record-fields dt{margin-bottom:4px}.record-list{padding-left:22px}.record-list li{margin:10px 0}.subprogram{min-width:0}.mini-note{overflow-wrap:anywhere}.facts{min-width:0}.facts dd{min-width:0}.subprogram h4{margin-top:24px}
@media(max-width:700px){.wrap{padding:0 16px}.city-switch a{flex:1 1 100%;white-space:normal}.brand{white-space:normal}.facts .facts>div{display:block}.record-list{padding-left:18px}.subprogram{padding-left:12px}.sources a,.facts a{word-break:break-word}.utilities{justify-content:flex-start;gap:8px}.utilities button{flex:1 1 auto}.mast{min-width:0}.hero h1{overflow-wrap:anywhere}}
'''
    assets=out/'assets';assets.mkdir(parents=True,exist_ok=True)
    (assets/'national-city.css').write_text(base_css+css_add,encoding='utf-8')
    js=city_js(kobe.find_all('script')[-1].string)
    (assets/'national-city.js').write_text(js,encoding='utf-8')
    for name in ('warm-shared.css', 'warm-city.css', 'warm-experience.js', 'family-guide.webp'):
        if (root/'assets'/name).resolve() != (assets/name).resolve():
            shutil.copy2(root/'assets'/name, assets/name)
    prefs,bus,taxi,supp,mobility=gather(root)
    indexed={(pid,c['slug']):(c,d) for pid,d in prefs.items() for c in d['cities']}
    wanted=[tuple(row['key'].split(':')) for row in supp['municipalities']]
    assert len(wanted)==1741 and len(set(wanted))==1741
    assert set(wanted)==set(indexed),'City enumeration differs between supplements and return records'
    grouped_count=0
    (assets/"seo.css").write_text((root/"assets/seo.css").read_text(encoding="utf-8"),encoding="utf-8")
    for pid,slug in wanted:
        c,d=indexed[(pid,slug)];a=adopted(pid,c,d,bus,taxi,supp,mobility)
        if (pid,slug) in HAND:
            doc=render_hand(reference/f'{pid}-{slug}.txt',pid,c,d,a)
        else:
            doc=render_generic(pid,c,d,a,kobe)
        content=make_city_content(pid,c,d,a)
        soup=BeautifulSoup(doc,'html.parser')
        soup.title.string=content['title']
        for attr,key,value in [('name','description',content['description']),('property','og:title',content['title']),('property','og:description',content['description'])]:
            meta=soup.find('meta',attrs={attr:key})
            if meta is None:
                meta=soup.new_tag('meta',attrs={attr:key});soup.head.append(meta)
            meta['content']=value
        soup.h1.clear();soup.h1.append(c['n']+'の免許返納特典と移動支援')
        for extra_heading in soup.find_all('h1')[1:]:
            extra_heading.name='h3'
        soup.select_one('.hero').insert_after(BeautifulSoup(content['intro_html'],'html.parser'))
        soup.head.append(soup.new_tag('link',rel='stylesheet',href='../assets/seo.css'))
        apply_warm_city(soup)
        for record_tag in soup.select('#preserved-records'):
            record_tag.decompose()
        if not draft:
            for banner in soup.select('.draftbar'):
                banner.decompose()
            for robots in soup.select('meta[name="robots"]'):
                robots.decompose()
        for note in soup.select('.print-only'):
            note.string='申請・利用前には、各制度の公式案内と窓口で最新の条件をご確認ください。'
        doc=str(soup)
        target=out/f'{pid}-menkyo-henno/{slug}.html';target.parent.mkdir(exist_ok=True);target.write_text(doc,encoding='utf-8')
        if a['bus']:grouped_count+=sum(aligned(c,p) for p in a['bus'].get('programs',[]))
    return {'cities':len(wanted),'handcrafted':len(HAND),'generic':len(wanted)-len(HAND),'bus_prefectures':len(bus),'unlisted_bus_cities':sum(pid not in bus for pid,slug in wanted),'mobility_cities':len(mobility),'return_bus_display_groups':grouped_count,'draft':draft}

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument('--out',type=Path)
    ap.add_argument('--draft',action='store_true')
    args=ap.parse_args()
    print(json.dumps(build_all(args.root,args.out or args.root,args.draft),ensure_ascii=False,indent=2))
