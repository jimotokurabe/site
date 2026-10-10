"""Search headings and first answers, derived only from already adopted records.

This module never edits records, fetches sources, or decides current entitlement.
Original factual sentences are retained whole: no amount-only or first-sentence
extraction that could omit a restriction, closure, or uncertainty.
"""
import html
import re


def e(value):
    return html.escape(str(value or ''), quote=True)


def values(value):
    if isinstance(value, str):
        return [value] if value and value != '記載なし' else []
    if isinstance(value, list):
        return [x for v in value for x in values(v)]
    return []


def unique(items):
    result=[]
    for item in items:
        if item and item not in result:
            result.append(item)
    return result


def sources(record, inherited, path):
    """Attach each source's own check date, preserving inherited dates separately."""
    result=[]
    local=record.get('checked') or inherited
    for i, source in enumerate(record.get('sources', [])):
        if isinstance(source, dict) and source.get('url'):
            result.append({'url':source['url'], 'label':source.get('label') or source.get('name') or '公式案内',
                           'checked':source.get('checked') or local,
                           'checked_key':f'{path}.sources[{i}].checked' if source.get('checked') else f'{path}.checked' if record.get('checked') else 'inherited',
                           'updated':source.get('updated') or source.get('date') or '',
                           'key':f'{path}.sources[{i}].url'})
    for key,label in [('url','公式案内'),('source','公式案内'),('link_url','特典の公式一覧'),('src_url','出典の案内')]:
        url=record.get(key)
        if isinstance(url,str) and url.startswith(('https://','http://')) and not any(s['url']==url for s in result):
            result.append({'url':url,'label':record.get('src') or record.get('link_label') or record.get('src_label') or label,
                           'checked':local, 'checked_key':f'{path}.checked' if record.get('checked') else 'inherited',
                           'updated':record.get('upd') or '', 'key':f'{path}.{key}'})
    return result


def part(label, text, key):
    return {'label':label,'text':str(text),'key':key}


def question(question, answer, anchor, record, checked, path, fields=(), cautions=(), state='recorded'):
    return {'question':question,'answer':answer,'anchor':anchor,'checked':record.get('checked') or checked,
            'keys':[path+'.'+k for k in fields], 'conditions':[], 'cautions':list(cautions),
            'sources':sources(record,checked,path),'state':state}


def conditions_from_return(q, c):
    guide=c.get('guide',{})
    facts=guide.get('facts',[])
    # Guide conditions can be more precise than a short table cell, e.g. a birth
    # date, return-period limitation, residence-at-return, or postal deadline.
    for label,field,pattern in [('対象・条件','age','対象'),('申請期限','dl','期限')]:
        chosen=[(i,row) for i,row in enumerate(facts) if isinstance(row,list) and len(row)==2 and re.search(pattern,str(row[0]))]
        if chosen:
            i,row=chosen[0]
            q['conditions'].append(part(label,row[1],f'return.guide.facts[{i}][1]'))
        elif values(c.get(field)):
            q['conditions'].append(part(label,c[field],f'return.{field}'))
    for key in ('note','flag'):
        for text in values(c.get(key)):
            q['cautions'].append(part('確認すること',text,f'return.{key}'))
    # Explicit cancellation, budget, and choice constraints are not compressed.
    for i,text in enumerate(guide.get('cautions',[])):
        if isinstance(text,str) and re.search(r'失効|すべて|全て|自主返納だけ|対象になる返納',text):
            q['cautions'].append(part('申請前の注意',text,f'return.guide.cautions[{i}]'))


def return_question(city,a):
    c=a['return'];state=c.get('k');name=city['n']
    answer=c.get('what') or '市町村独自の免許返納特典の内容は、掲載情報では確認できていません。'
    if state=='end':
        heading=f'{name}の返納特典は、今も申し込めますか？'
        answer='終了した返納支援の記録です。'+answer
    elif state=='notfound':
        heading=f'{name}独自の免許返納特典はありますか？'
        answer='掲載調査では、市町村独自の返納特典を確認できていません。'+answer
    elif state=='none':
        heading=f'{name}独自の免許返納特典はありますか？'
    elif state=='elder':
        heading=f'返納後に使う高齢者支援の条件は？'
    else:
        heading=f'{name}の免許返納で、どんな支援がありますか？'
    q=question(heading,answer,'benefit',c,a.get('return_checked'),'return',('k','what'),state=state or 'unknown')
    conditions_from_return(q,c)
    return q


def statewide_question(a,prefname):
    record=a.get('statewide') or {}
    common=a.get('common',{}).get('tokuten',{})
    if record and values(record.get('body')):
        # All body paragraphs are evidence; the primary condition paragraph is
        # shown whole, further explanations stay in the linked detailed section.
        answer=values(record['body'])[0]
        q=question(f'{prefname}で共通の返納支援は？',answer,'benefit',record,a.get('common_checked'),'statewide',('body[0]',))
        q['sources']+=sources(common,a.get('common_checked'),'common.tokuten')
        for i,text in enumerate(values(record['body'])[1:],1):
            q['conditions'].append(part('条件・補足',text,f'statewide.body[{i}]'))
    elif common and (values(common.get('what')) or values(common.get('who'))):
        answer=' '.join(values(common.get('who'))+values(common.get('what')))
        q=question(f'{prefname}で共通の返納支援は？',answer,'benefit',common,a.get('common_checked'),'common.tokuten',('who','what'))
    else:
        return None
    return q


def bus_question(a):
    b=a.get('bus')
    if b is None:
        return question('高齢者向けのバス助成はありますか？','自治体別のバス助成データは未掲載です。このページの記録だけでは、制度の有無や対象路線を確認できていません。','support',{},None,'bus',state='unlisted')
    status=b.get('status')
    programs=b.get('programs',[])
    regular=[(i,p) for i,p in enumerate(programs) if p.get('kind')!='henno']
    if status in ('unknown','ended','notfound') or not regular:
        prefix={'unknown':'対象・料金・現在の受付は確認が必要です。','ended':'終了したバス支援の記録です。',
                'notfound':'掲載調査では、自治体独自の高齢者向けバス助成を確認できていません。',
                'henno':'掲載されているのは免許返納に関連する支援です。'}.get(status,'')
        q=question('返納とは別の高齢者バス助成はありますか？',prefix+(b.get('summary') or '通常の高齢者向けバス助成の条件は確認できていません。'),
                   'support',b,a.get('bus_checked'),'bus',('status','summary'),state=status or 'unknown')
        if status=='henno':
            q['conditions'].append(part('支援の区別','返納者向け支援を、高齢者全員が使える制度とは扱っていません。','bus.status'))
    else:
        i,p=regular[0];path=f'bus.programs[{i}]'
        warning='現在の適用条件は確認が必要です。' if p.get('current')=='needs_confirmation' else ''
        answer=warning+p.get('name','掲載されている制度')+'：'+(p.get('benefit') or b.get('summary') or '支援内容は確認が必要です。')
        q=question('掲載されている高齢者のバス支援は？',answer,'support',p,p.get('checked') or a.get('bus_checked'),path,('name','kind','current','benefit'),state=p.get('current') or status)
        for label,key in [('対象・条件','eligibility'),('本人負担・運賃','fare')]:
            if values(p.get(key)):
                q['conditions'].append(part(label,p[key],path+'.'+key))
        for j,text in enumerate(values(p.get('notes'))):
            q['cautions'].append(part('利用前の注意',text,f'{path}.notes[{j}]'))
        if len(regular)>1:
            q['conditions'].append(part('ほかの制度',f'このほかにも掲載情報があります。各制度の対象・条件は詳細欄で確認してください。','bus.programs'))
    for text in values(b.get('flag')):
        q['cautions'].append(part('確認すること',text,'bus.flag'))
    if not q['sources']:
        q['sources']=sources(b,a.get('bus_checked'),'bus')
    return q


TITLE_OVERRIDES={
    ('hyogo','kobe'):'免許返納のICOCA配布終了・県内割引と敬老パス',
    ('kanagawa','yokohama'):'敬老パス｜通常の負担と免許返納者の無料交付条件',
    ('hyogo','nishinomiya'):'免許返納特典｜市独自特典なし・県内割引とバス助成',
    ('hyogo','akashi'):'免許返納特典｜ICOCAか図書カード3,000円分・申請期限',
    ('hyogo','kawanishi'):'免許返納特典｜ICOCA・hanica・定期券支援の選択と条件',
    ('kagoshima','kagoshima'):'免許返納者割引と敬老パス｜対象・負担・変更予定',
}


def notfound_parts(a,prefname):
    """独自特典が見つからなかった市町村のページに、実際に載っているものだけを並べる。"""
    c=a['return'];parts=[]
    if a.get('statewide') or a.get('common',{}).get('tokuten'):parts.append(prefname+'共通の特典')
    if a.get('common',{}).get('hennou'):parts.append('返納手続き')
    if values(c.get('apply')) and '記載なし' not in values(c.get('apply')):parts.append('問い合わせ先')
    return parts


def title_content(pid,city,a):
    c=a['return'];state=c.get('k');b=a.get('bus');text=' '.join(values(c.get('what'))+values(c.get('amt')))
    key=(pid,city['slug'])
    if key in TITLE_OVERRIDES:
        return city['n']+'の'+TITLE_OVERRIDES[key]+'｜じもとくらべ', ['return.k','return.what']+(['return.guide'] if c.get('guide') else [])+(['bus.programs'] if b else [])
    # Exact record terms determine which concrete content is emphasized. Amounts
    # are never independently extracted or advertised as a maximum entitlement.
    labels=[]
    for pattern,label in [(r'ICOCA','ICOCA'),(r'hanica','hanica'),(r'マナカ|manaca','マナカ'),(r'SUGOCA','SUGOCA'),
                          (r'図書カード','図書カード'),(r'商品券','商品券'),(r'タクシー','タクシー支援'),
                          (r'バス','バス支援'),(r'定期券','定期券支援'),(r'自転車','自転車購入支援'),
                          (r'経歴証明書.*(手数料|交付費用)|(手数料|交付費用).*経歴証明書','経歴証明書の手数料助成')]:
        if re.search(pattern,text):labels.append(label)
    topic='・'.join(labels[:2])
    if state in ('end','notfound','none'):
        prefix={'end':'免許返納支援の終了情報','notfound':'免許返納の支援','none':'免許返納の市町村独自特典なし'}[state]
        prefname=a.get('prefname','')
        if b and b.get('status')=='active':
            regular=[p for p in b.get('programs',[]) if p.get('kind')!='henno']
            suffix='敬老パスの対象・条件' if any('敬老' in p.get('name','') and 'パス' in p.get('name','') for p in regular) else 'バス支援の対象・条件'
        elif a.get('statewide') or a.get('common',{}).get('tokuten'):
            # 独自特典が見つからなかった市町村は、ページに載っている県共通の特典・手続き・問い合わせ先を題名にする
            suffix=('・'.join(notfound_parts(a,prefname))) if state=='notfound' and prefname else '都道府県の支援情報'
        else:suffix=('・'.join(notfound_parts(a,prefname)) or '支援の確認状況') if state=='notfound' else '手続きと支援情報'
        content=prefix+'｜'+suffix
    elif state=='elder':content='免許返納と'+(topic or '高齢者支援')+'の条件'
    elif state=='discount':content='免許返納の割引｜'+(topic+'の条件' if topic else '対象・利用条件')
    elif state=='purchase':content='免許返納の購入費補助｜'+(topic+'の条件' if topic else '対象・申請条件')
    else:content='免許返納特典｜'+(topic+'の条件・申請方法' if topic else '支援内容・対象・申請方法')
    return city['n']+'の'+content+'｜じもとくらべ', ['return.k','return.what']+(['return.amt'] if values(c.get('amt')) else [])+(['bus.status','bus.programs'] if b else [])+(['statewide'] if a.get('statewide') else [])


def taxi_question(a):
    t=a.get('taxi')
    if not t or t.get('k') not in ('yes','care','henno_only') or t.get('guide_relation')=='same':
        return None
    heading='要介護者等向けのタクシー支援は？' if t.get('k')=='care' else 'タクシー支援の対象・内容は？'
    q=question(heading,t.get('what') or 'タクシー支援の対象は、詳細の記録で確認してください。','taxi',t,a.get('taxi_checked'),'taxi',('k','what'),state=t.get('k'))
    for label,key in [('対象・条件','age'),('返納との関係','henno_link')]:
        if values(t.get(key)):q['conditions'].append(part(label,t[key],'taxi.'+key))
    for key in ('note','flag'):
        for text in values(t.get(key)):q['cautions'].append(part('確認すること',text,'taxi.'+key))
    return q


def render_question(q,index):
    h=f'<article class="answer-item"><h3>{e(q["question"])}</h3><p class="answer-text">{e(q["answer"])}</p>'
    core=[p for p in q['conditions'] if p['label']!='条件・補足']
    extra=[p for p in q['conditions'] if p['label']=='条件・補足']
    if core:
        h+='<dl class="answer-conditions">'+''.join('<div><dt>'+e(p['label'])+'</dt><dd>'+e(p['text'])+'</dd></div>' for p in core)+'</dl>'
    caution=unique([p['text'] for p in q['cautions']])
    visible=[text for text in caution if re.search(r'予算|終了|期限|変更予定|年度以降',text)]
    folded=[text for text in caution if text not in visible]
    if visible:
        h+='<div class="answer-cautions">'+''.join('<p>'+e(text)+'</p>' for text in visible)+'</div>'
    h+='<p class="answer-date">この内容の確認日：'+e(q['checked'] or '未記録')+'</p>'
    if folded or extra or q['sources']:
        h+='<details class="answer-evidence"><summary>注意事項・出典と確認日</summary>'
        h+=''.join('<p>'+e(p['text'])+'</p>' for p in extra)
        h+=''.join('<p class="answer-caution-detail">'+e(text)+'</p>' for text in folded)
        if q['sources']:
            h+='<ul class="answer-sources">'+''.join('<li><a href="'+e(s['url'])+'">'+e(s['label'])+' ↗</a><span>この出典の確認日：'+e(s['checked'] or '未記録')+'</span></li>' for s in q['sources'][:2])+'</ul>'
            if len(q['sources'])>2:h+='<p class="answer-date">関連するほかの出典と各確認日は、下の詳細欄に掲載しています。</p>'
        else:h+='<p>この回答に対応する公式出典は、掲載情報では確認できていません。</p>'
        h+='</details>'
    elif not q['sources']:
        h+='<p class="answer-date">この回答に対応する公式出典は、掲載情報では確認できていません。</p>'
    h+='<a class="answer-detail" href="#'+e(q['anchor'])+'">対象・条件・申請先を詳しく確認する ↓</a></article>'
    return h


def make_city_content(pid,city,pref_data,adopted):
    a=adopted;key=(pid,city['slug']);c=a['return'];prefname=pref_data['pref']['name'];a['prefname']=prefname
    title,title_keys=title_content(pid,city,a)
    title=title.replace(city['n']+'の',city['n']+'（'+prefname+'）の',1)
    questions=[return_question(city,a)]
    state=c.get('k')
    if state in ('end','none','notfound'):
        sq=statewide_question(a,pref_data['pref']['name'])
        if sq:questions.append(sq)
    bq=bus_question(a)
    tq=taxi_question(a)
    if tq and (not a.get('bus') or a['bus'].get('status')=='notfound'):
        bq=tq
        if c.get('k') in ('end','notfound','none'):
            title=re.sub(r'｜(?:都道府県の支援情報|手続きと支援情報|.+共通の特典・返納手続き・問い合わせ先|返納手続き・問い合わせ先)｜じもとくらべ$', '｜タクシー支援の対象・条件｜じもとくらべ',title)
            title_keys.append('taxi')
    # Henno-only bus records repeat the same municipal benefit. Show their
    # distinction as one concise note on the first answer, not another overview.
    if a.get('bus') and a['bus'].get('status')=='henno':
        questions[0]['cautions'].append(part('バス支援の区別',a['bus'].get('summary','通常の高齢者向けバス助成は確認できていません。'),'bus.summary'))
        questions[0]['cautions']+=bq['cautions']
        questions[0]['sources']+= [s for s in bq['sources'] if not any(old['url']==s['url'] and old['checked']==s['checked'] for old in questions[0]['sources'])]
    else:questions.append(bq)
    # Preserve special qualifications across differing source versions. These
    # labels explain the existing records; they do not reconcile them as new facts.
    if key==('kanagawa','yokohama'):
        questions[0]['question']='免許返納で敬老パスの負担が無料になる条件は？'
        p=a['bus']['programs'][1];path='bus.programs[1]'
        questions[0]['answer']=p['benefit']
        questions[0]['conditions']=[part('対象・申請期限',p['eligibility'],path+'.eligibility')]
        questions[0]['keys']=[path+'.benefit',path+'.current']
        questions[0]['cautions']=[v for v in questions[0]['cautions'] if not v['key'].startswith('return.guide.cautions')]
        questions[0]['sources']=sources(p,a.get('bus_checked'),path)
        questions[0]['checked']=p.get('checked') or a.get('bus_checked')
        questions[-1]['question']='70歳以上の通常の敬老パスは無料ですか？'
    if key==('hyogo','kobe'):
        questions[0]['question']='返納するとICOCA 5,000円分はもらえますか？'
    if key==('hyogo','akashi'):
        questions[0]['question']='返納特典はICOCAと図書カードの両方をもらえますか？'
    if key==('hyogo','kawanishi'):
        questions[0]['question']='ICOCA・hanica・定期券支援は、どれを選べますか？'
    if key==('kagoshima','kagoshima'):
        questions[0]['question']='免許返納者の市営バス・市電割引は？'
        p=a['bus']['programs'][2];path='bus.programs[2]'
        questions[0]['answer']='年齢・対象範囲などは確認が必要です。'+p['benefit']
        questions[0]['conditions']=[part('対象・確認が必要な点',p['eligibility'],path+'.eligibility')]
        questions[0]['keys']=[path+'.benefit',path+'.current']
        questions[0]['sources']=sources(p,a.get('bus_checked'),path)
        questions[0]['checked']=p.get('checked') or a.get('bus_checked')
        questions[0]['state']=p['current']
        questions[-1]['question']='70歳以上の敬老パスの負担は変わりますか？'
    questions=questions[:3]
    topic=title.split('）の',1)[-1].rsplit('｜じもとくらべ',1)[0].replace('｜','、')
    description=prefname+'の'+city['n']+'。'+topic+'を、掲載情報から確認できます。'
    status_line={'end':'終了した返納支援の案内を含みます。','notfound':'市町村独自の返納特典は掲載調査では確認できていません。',
                 'none':'市町村独自の返納特典がないとする公式案内を掲載しています。'}.get(state,'対象・申請期限・公式出典と確認日を掲載しています。')
    if state=='notfound':
        # 何が載っているかを先に書く（独自特典の有無だけで終わらせない）
        parts=notfound_parts(a,prefname);parts.insert(len(parts)-1 if '問い合わせ先' in parts else len(parts),'バス・タクシー支援の確認状況')
        description=(prefname+'の'+city['n']+'。独自の返納特典は公式ページで確認できませんでした（確認日 '+str(a.get('return_checked') or '未記録')+'）。'
                     +'・'.join(parts)+'を掲載しています。')
    else:description+=status_line
    if a.get('bus') and a['bus'].get('status')=='unknown':description+='バス支援の現在の条件は要確認です。'
    intro='<aside class="search-answer" id="quick-answer" aria-labelledby="quick-answer-title"><h2 id="quick-answer-title">まず知っておきたいこと</h2><p class="answer-intro">掲載情報から、よくある疑問を確認できます。</p>'+''.join(render_question(q,i) for i,q in enumerate(questions))+'</aside>'
    audit={'key':pid+':'+city['slug'],'title':title,'title_evidence_keys':title_keys,'return_state':state,
           'bus_state':a['bus'].get('status') if a.get('bus') else 'unlisted',
           'questions':questions,'policy':'Existing adopted records only; complete factual sentences; source-local checked dates retained.'}
    return {'title':title,'description':description,'intro_html':intro,'audit':audit}
