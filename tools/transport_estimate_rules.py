#!/usr/bin/env python3
"""Build only conservative transport estimates from recorded outing-support data.

This is a local, deterministic parser. It does not fetch or re-verify source pages.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / 'assets' / 'outing-supports'
RULES_PATH = ROOT / 'data' / 'transport-estimate-reviewed.json'
AUDIT_PATH = ROOT / 'docs' / 'estimate-rule-audit.json'

# The separately maintained initial pilot rules belong to the parent task.
PILOT_KEYS = {
    'hyogo:akashi', 'hyogo:nishinomiya', 'hyogo:sanda', 'hyogo:takasago',
    'hyogo:himeji', 'hyogo:aioi', 'hyogo:inami',
    'nara:kawanishi', 'nara:miyake', 'nara:tawaramoto',
}
NON_SUBSIDY_FIXED_PROGRAMS = {
    'taxi-7d3fbd12873eb7d2',  # 伊達市: shared ride fare itself
    'taxi-c319bd321b0c2cdb',  # 湯河原町: shared ride fare itself
    'taxi-2837a392e5ade1c9',  # 坂城町: shared ride fare itself
}

YEN_RE = re.compile(r'(?<![\d,])([\d,]+)\s*円')
FACE_RE = re.compile(r'(?:1枚|一枚|券1枚|利用券1枚|助成券1枚|タクシー券1枚)\s*([\d,]+)\s*円')
ANNUAL_STOCK_RE = re.compile(r'(?:年間|年(?:間)?|毎年|毎年度|各年度)\s*(?:最大|上限)?\s*([\d,]+)\s*枚')
PER_RIDE_CAP_RE = re.compile(r'(?:1回|1乗車|一回|一乗車)(?:の乗車|あたり|につき|で|に)?[^。\n]{0,18}?(?:最大|上限)?\s*([\d,]+)\s*枚')
FIXED_RE = re.compile(r'(?:1乗車|一乗車|1回|一回)(?:につき|あたり|で)?\s*(?:1人あたり)?\s*([\d,]+)\s*円')
RATE_RE = re.compile(r'(?:運賃|料金)[^。\n]{0,12}?(半額|([1-9])割(?:引|を助成|助成)|([1-9])割引|([1-9])\s*[％%](?:引|割引|助成)?)')
BLOCKER_RE = re.compile(r'終了|受付終了|廃止|終了予定|予算到達|年度に限り|年度限り|申請月|交付月|決定月|月ごと|毎月|1か月|1ヶ月|月あたり|月額|月\s*\d+\s*(?:枚|回)|\d+枚.{0,12}月\s*\d+枚|\d+月|\d{4}年|令和[0-9元]+年度|平成[0-9]+年度|選択|いずれか|それぞれ|区分|に応じ|応じて|別に|併用|併給|他の制度|同伴者|小学生|各乗車券|回数券|定期券|返納.{0,35}(?:1回|一回|1度|一度|限り|\d+年間)|(?:1回|一回|限り|\d+年間).{0,35}返納')


def read_catalog():
    for path in sorted(SOURCE_DIR.glob('*.json')):
        if path.name == 'index.json':
            continue
        prefecture = path.stem
        data = json.loads(path.read_text(encoding='utf-8'))
        for city in data.get('cities', []):
            for program in city.get('programs', []):
                yield prefecture, city, program


def detail_map(program):
    return {row.get('label', ''): row.get('text', '') for row in program.get('details', [])}


def find_rule(prefecture, city, program, details, rule_type, values):
    evidence = details.get('支援内容', '').strip()
    eligibility = '\n'.join(f"{row.get('label', '')}: {row.get('text', '')}" for row in program.get('details', []) if row.get('text', '').strip())
    assumption = ('年度初めに未使用の年間交付券が揃い、掲載記録の対象条件を満たす場合の参考比較。利用回数と実際の残数は利用者の状況で変わります。'
                  if rule_type == 'coupon' else
                  '乗車証等を持っている人の乗車料金だけの例。掲載記録の対象条件を満たし、同じ条件が1年間続く場合の参考比較です。')
    rule = {
        'id': f"transport:{prefecture}:{city['id']}:{program['id']}",
        'key': f"{prefecture}:{city['id']}",
        'programId': program['id'],
        'type': program['type'],
        'kind': rule_type,
        **values,
        'rounding': 'floor',
        'annualFee': 0,
        'cycle': 'annual' if rule_type == 'coupon' else 'ongoing',
        'title': program.get('name', '交通支援'),
        'headline': '',
        'assumption': assumption,
        'eligibility': eligibility,
        'checked': program.get('checked', ''),
        'sources': program.get('sources', []),
        'evidence': evidence,
        'origin': 'record',
    }
    if rule.get('cap') is None:
        rule.pop('cap', None)
    if rule_type == 'coupon':
        rule['headline'] = f"年間最大{values['face'] * values['stock']:,}円分（利用券）"
    elif rule_type == 'percent':
        rule['headline'] = f"運賃の{values['percent']}%を割引"
    else:
        rule['headline'] = f"1回{values['fixedFare']:,}円"
    return rule


def classify(prefecture, city, program, details, selectable_type_count):
    # Hard gates: recorded/selectable facts only; never turn absence or ended records into rules.
    if not program.get('selectable') or program.get('status') != '掲載記録あり・対象条件を確認':
        return None, 'not_selectable_or_not_current_record'
    if not program.get('sources'):
        return None, 'no_source'
    if not program.get('checked'):
        return None, 'no_recorded_check_date'
    if f"{prefecture}:{city['id']}" in PILOT_KEYS:
        return None, 'pilot_rule_owned_elsewhere'
    if program.get('id') in NON_SUBSIDY_FIXED_PROGRAMS:
        return None, 'fixed_fare_is_service_fare_not_subsidy'

    text = details.get('支援内容', '').strip()
    if not text or text == '記載なし':
        return None, 'no_explicit_support_formula'
    if not (details.get('対象・条件') or details.get('対象・年齢') or details.get('対象者') or details.get('内容')):
        return None, 'no_recorded_eligibility_description'
    joined = '\n'.join([program.get('name', ''), details.get('支援内容', ''), details.get('内容', ''),
                         details.get('対象・条件', ''), details.get('対象・年齢', ''),
                         details.get('本人負担・運賃', ''), details.get('補足・注意', ''),
                         details.get('他の支援との関係', ''), details.get('確認が必要な点', ''),
                         details.get('申請方法', '')])
    if BLOCKER_RE.search(joined):
        return None, 'time_variant_choice_or_cross_program_ambiguity'
    if details.get('他の支援との関係', '').strip() not in ('', '記載なし', 'なし'):
        return None, 'cross_program_relation_needs_review'
    if details.get('確認が必要な点', '').strip() not in ('', '記載なし', 'なし'):
        return None, 'record_explicitly_requires_confirmation'
    if re.search(r'登録料|更新料|年会費|購入費|カード購入費|会費|加入料|申込料', joined):
        return None, 'fee_not_represented_in_schema'
    # Do not assume a single record can be split into multiple services, rate tiers, or payment methods.
    if any(token in text for token in ('／', '/', '〜', '～', 'または', 'かつ', '・', '別途', '無料', '通常料金', '通常運賃')):
        return None, 'multiple_tiers_or_components'
    if '共通' in program.get('name', '') or ('バス' in text and 'タクシー' in text):
        return None, 'multiple_modes_share_or_mix_support'

    # Coupon: one explicit unit face value, fixed annual stock, and explicit per-ride cap.
    faces = list(FACE_RE.finditer(text))
    stocks = list(ANNUAL_STOCK_RE.finditer(text))
    if len(faces) == 1 and len(stocks) == 1:
        # Explicit monthly issue limits are deliberately excluded because this rule has no calendar schedule.
        if not re.search(r'申請月|年度途中|月あたり|毎月|1か月|1ヶ月|月ごと', text):
            if re.search(r'夫|妻|世帯|どちらか|場合[^。\n]{0,30}\d+枚|限度とする', text):
                return None, 'coupon_has_multiple_recipient_or_value_tiers'
            yen_values = {int(v.replace(',', '')) for v in YEN_RE.findall(text)}
            face = int(faces[0].group(1).replace(',', ''))
            stock = int(stocks[0].group(1).replace(',', ''))
            # Unit value and its explicit product total are okay; unexplained values indicate a mixed rule.
            allowed_values = {face}
            permitted_yen_values = allowed_values | {face * stock}
            if yen_values <= permitted_yen_values:
                caps = list(PER_RIDE_CAP_RE.finditer(text))
                if len(caps) == 1:
                    cap = int(caps[0].group(1).replace(',', ''))
                    return find_rule(prefecture, city, program, details, 'coupon', {'face': face, 'stock': stock, 'cap': cap}), 'accepted_coupon'
                return None, 'coupon_missing_explicit_per_ride_cap'
        return None, 'coupon_has_monthly_or_additional_limit'

    # Fixed passenger fare: one unambiguous amount for each qualifying trip.
    fixed = list(FIXED_RE.finditer(text))
    yen_values = {int(v.replace(',', '')) for v in YEN_RE.findall(text)}
    if len(fixed) == 1 and len(yen_values) == 1:
        fare = int(fixed[0].group(1).replace(',', ''))
        if not re.search(r'半額|半分|割引|引き|助成|上限|まで|以下|以上|距離|区域|地域|同乗|乗合人数|場合|対象外|通常|ICカード', text):
            return find_rule(prefecture, city, program, details, 'fixed', {'fixedFare': fare}), 'accepted_fixed'
        return None, 'fixed_fare_has_conditions_or_caps'

    # A single unbounded rate only. Multiple rates, yen caps, and usage limits need another model.
    rates = list(RATE_RE.finditer(text))
    if len(rates) == 1 and not YEN_RE.search(text) and not re.search(r'上限|まで|年間|年\d|回数|枚|回|月|段階|年齢|区分|条件|利用登録|カード', text):
        hit = rates[0]
        token = hit.group(1)
        percent = 50 if token == '半額' else int(hit.group(2) or hit.group(3) or hit.group(4)) * (10 if '割' in token else 1)
        if 0 < percent < 100:
            return find_rule(prefecture, city, program, details, 'percent', {'percent': percent}), 'accepted_percent'
    return None, 'formula_not_a_supported_single_pattern'


def main():
    rows = list(read_catalog())
    city_type_count = Counter(
        (prefecture, city['id'], program.get('type'))
        for prefecture, city, program in rows
        if program.get('selectable') and program.get('status') == '掲載記録あり・対象条件を確認'
    )
    rules = []
    reasons = Counter()
    by_kind = Counter()
    by_prefecture = Counter()
    for prefecture, city, program in rows:
        if program.get('type') not in ('taxi', 'bus'):
            continue
        details = detail_map(program)
        count = city_type_count[(prefecture, city['id'], program.get('type'))]
        rule, reason = classify(prefecture, city, program, details, count)
        reasons[reason] += 1
        if rule:
            rules.append(rule)

    # Identical formulas in the same municipality can be separate eligibility routes;
    # without a documented relationship, omit all duplicates rather than count them twice.
    def signature(rule):
        return tuple((rule.get(k) if k != 'sources' else None) for k in
                     ('key', 'type', 'kind', 'evidence', 'face', 'stock', 'cap', 'percent', 'fixedFare'))
    grouped = {}
    for rule in rules:
        grouped.setdefault(signature(rule), []).append(rule)
    deduped = []
    for group in grouped.values():
        if len(group) > 1:
            reasons['duplicate_or_competing_identical_records'] += len(group)
        else:
            deduped.extend(group)
    rules = deduped
    for rule in rules:
        by_kind[rule['kind']] += 1
        by_prefecture[rule['key'].split(':', 1)[0]] += 1

    rules.sort(key=lambda r: (r['key'], r['type'], r['programId']))
    RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    RULES_PATH.write_text(json.dumps({'schemaVersion': 1, 'rules': rules}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    audit = {
        'title': '全国交通費概算ルールの抽出監査',
        'auditDate': '2026-10-15',
        'catalogScope': 'assets/outing-supports の47都道府県JSON。データ記録だけを使用し、外部確認や確認日の更新なし。',
        'prefectureFiles': 47,
        'municipalitiesInIndex': 1741,
        'recordsScanned': len(rows),
        'rulesIncluded': len(rules),
        'candidateRuleCountsBeforeDedup': {
            'coupon': reasons['accepted_coupon'], 'fixed': reasons['accepted_fixed'], 'percent': reasons['accepted_percent']
        },
        'rulesByKind': dict(sorted(by_kind.items())),
        'rulesByPrefecture': dict(sorted(by_prefecture.items())),
        'classificationCounts': dict(sorted(reasons.items())),
        'exclusionCounts': dict(sorted((k, v) for k, v in reasons.items() if not k.startswith('accepted_'))),
        'strictGates': [
            'selectable=true、statusが掲載記録あり・対象条件を確認、sourceと既存checkedあり。',
            '親が別管理する10自治体を除外。別制度はrule idと対象条件ごとに保持し、同じ自治体でも自動合算しない。数値と式が同一の重複レコードは全て除外。',
            '券: 支援内容に単一の1枚額、固定の年間枚数、明示された1乗車上限枚数があり、月ごとの交付条件がない。',
            '定額: 支援内容に1乗車/1回あたりの単一本人運賃が明記され、割引・助成額・料金段階・地域別額・上限ではない。',
            '率: 単一率で、円上限・年回数・条件分岐がない。',
            '終了、年度限定、申請月/交付月変動、選択制、段階別、他制度との関係が記録される場合は安全側に除外。'
        ],
        'schemaInterpretation': {
            'coupon': 'faceは券面額、stockは1年間の最大交付枚数、capは元記録に明記された1乗車の最大枚数。capが不明な券はルール化しない。運賃→割引→min(floor又はceil(運賃÷face), cap, 残枚数)→助成額min(運賃, 枚数×face)の順。',
            'percent': 'percentは割引率の整数（50=50%）。',
            'fixed': 'fixedFareは対象者の1乗車あたり本人運賃（円）。乗合交通そのものの運賃は、比較前運賃が明確でない場合に負担減と誤称するため除外。',
            'rounding': 'floor。',
            'cycle': 'couponはannual、rate/fixedはongoing。いずれも比較期間は1年。'
        },
        'reviewedExamples': [],
        'excludedReasons': {
            'data_text_is_not_a_formula': 'カタログは制度説明文であり、全文を計算式とみなさない。文面から対象者の適格性や利用条件を判定できないときはルール化せず除外。',
            'provincial_common_and_duplicates': '市町村単位のレコードに県共通・広域・共同運行制度が重複しうる。制度IDだけでなく対象区域/実施主体を照合しない限り、市町村ごとの独立制度として重複計上しない。',
            'ended_or_unconfirmed': '未確認・終了・支援なしは計算対象にしない。',
            'once_or_annual': '返納時1回限りは毎年の概算へ加算しない。',
            'choice_and_tiers': '交通種別・運賃方式・年齢区分・申請月による選択や段階を合算しない。返納後の期限付き割引は継続制度と混同しない。',
            'caps_and_actual_usage': '最大交付数から実残数は分からない。年間枠、1乗車あたり枚数上限、運賃を超えない制限の範囲で利用する前提で表示し、実利用・年度途中申請・期限切れを推定しない。',
            'separate_programs': '同じ自治体に複数ルールがある場合も、対象条件ごとに別に表示する。明示的な併用可の記録がない限り助成額を合算しない。詳細欄には元の全詳細文を保持する。'
        },
        'limitations': [
            'ルールは既存カタログの記録に基づく保守的な候補で、公式ページの現在状態を再確認したものではない。checkedとsourcesは元記録の値を保持する。',
            'eligibility文字列は記録上の対象条件であり、計算画面に入力を要求せず、対象条件を満たす人の参考比較として提示する。',
            '支援額の計算には利用回数・通常運賃が必要な類型があり、結果は仮の条件での比較。実際の利用可否や残高を示さない。'
        ]
    }
    review_specs = [
        ('aichi', '東郷町', 'taxi', 'タクシー'), ('chiba', '長生村', 'taxi', '福祉タクシー'),
        ('gifu', '垂井町', 'taxi', '高齢者タクシー'), ('gunma', '吉岡町', 'taxi', 'よしタク'),
        ('hokkaido', '伊達市', 'taxi', '愛のりタクシー'), ('hokkaido', '東川町', 'taxi', 'ハイヤー'),
        ('hokkaido', '中頓別町', 'taxi', 'ハイヤー乗車券'), ('hyogo', '尼崎市', 'taxi', '移送サービス'),
        ('hyogo', '加西市', 'taxi', '高齢者タクシー'), ('ibaraki', '古河市', 'bus', 'シルバーパス'),
        ('ibaraki', '小美玉市', 'bus', '半額'), ('kagawa', '東かがわ市', 'bus', '福祉バス'),
        ('kanagawa', '湯河原町', 'taxi', 'タクシー'), ('miyagi', '大和町', 'bus', '70歳以上'),
        ('miyazaki', '小林市', 'taxi', '福祉タクシー'), ('nagano', '立科町', 'taxi', '利用サポート'),
        ('shimane', '松江市', 'bus', '優待ICOCA'), ('tottori', '若桜町', 'taxi', 'タクシー'),
        ('toyama', '朝日町', 'taxi', 'シルバータクシー'), ('shizuoka', '河津町', 'taxi', 'おでかけ支援')
    ]
    samples = []
    included_ids = {r['programId'] for r in rules}
    for pref, city_name, typ, name_hint in review_specs:
        found = next(((pr, c, p) for pr, c, p in rows if pr == pref and c['name'] == city_name
                      and p.get('type') == typ and name_hint in p.get('name', '')
                      and p.get('selectable') and p.get('status') == '掲載記録あり・対象条件を確認'), None)
        if not found:
            continue
        pr, c, p = found
        d = detail_map(p)
        candidate, reason = classify(pr, c, p, d, city_type_count[(pr, c['id'], typ)])
        if candidate and p['id'] not in included_ids:
            candidate, reason = None, 'duplicate_or_competing_identical_records'
        samples.append({
            'key': f"{pr}:{c['id']}", 'programId': p['id'], 'type': typ,
            'program': p.get('name', ''), 'supportContentFull': d.get('支援内容', ''),
            'decision': '採用' if candidate else '除外', 'reason': reason,
            'review': '単一式と必須数値を保持できるか、複数額・段階・月別配布・終了/選択・返納一回限り・追加確認事項がないかを確認。'
        })
    audit['reviewedExamples'] = samples
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
