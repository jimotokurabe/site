"""Generate the nationwide, private-by-default outing worksheet."""
from bs4 import BeautifulSoup
from site_header import apply_site_header


def outing_plan_page(shell, draft=False):
    main = '''<nav class="crumbs" aria-label="現在の場所"><a href="index.html">トップ</a> ／ お出かけ計画</nav>
<header class="outing-hero">
  <div><p class="outing-kicker">免許返納の前も、車を使わない日も。</p>
  <h1>いつもの病院やお店へ、<br>車なしで通うには？</h1>
  <p>行く場所をひとつ決めて、往復の方法と費用を整理。<br>地元の支援も見ながら、本人や家族で検討できます。</p><a class="outing-start-link" href="#outing-step-0">行く場所から考える ↓</a></div>
  <div class="outing-route" aria-label="病院への往復を考える例"><p class="outing-example-label">例えば、かかりつけの病院へ</p>
    <svg viewBox="0 0 420 150" role="img" aria-label="家・行き先・家をつなぐ往復の道">
      <path d="M70 93 Q150 15 210 93 T355 93" fill="none" stroke="#285b40" stroke-width="3" stroke-dasharray="5 7"/>
      <g stroke="#285b40" stroke-width="3" stroke-linejoin="round"><path d="M24 93V57L59 30l35 27v36z" fill="#b9ded5"/><path d="M49 93V68h20v25" fill="#fffefb"/><path d="M174 97V55h76v42z" fill="#f4d999"/><path d="M167 55l11-25h68l11 25z" fill="#edc7bc"/><path d="M204 97V69h17v28" fill="#fffefb"/><path d="M316 93V57l35-27 35 27v36z" fill="#d8e9f2"/><path d="M341 93V68h20v25" fill="#fffefb"/></g>
      <g fill="#285b40" font-size="17" text-anchor="middle"><text x="59" y="132">家</text><text x="211" y="132">病院</text><text x="351" y="132">家</text></g>
    </svg>
    <div class="outing-example-legs"><span>行きはバス？</span><span>帰りはタクシー？</span></div><p class="outing-note">帰りの時間が読めない日も、別々に考えられます。</p>
  </div>
</header>
<ul class="outing-benefits" aria-label="このページで整理できること"><li><span aria-hidden="true">↔</span><div><strong>どう往復する？</strong><small>行きと帰りを別々に検討</small></div></li><li><span aria-hidden="true">¥</span><div><strong>いくらかかる？</strong><small>入力した費用と支援利用後を比較</small></div></li><li><span aria-hidden="true">✓</span><div><strong>次に何を調べる？</strong><small>未確認のことを家族と共有</small></div></li></ul>
<div class="outing-layout">
<div class="outing-work">
<p class="outing-note">分かるところだけで大丈夫。経路や運賃の自動検索ではなく、調べた内容と未確認のことを整理するページです。</p>
<noscript><p>計画をまとめるにはJavaScriptを有効にしてください。行き先・行きと帰りの交通・費用・予約・困ったときの代案を紙に書いて準備することもできます。</p></noscript>
<div id="outing-app" hidden>
<ol class="outing-progress" aria-label="計画づくりの進み具合"><li aria-current="step"><span class="outing-step-number" aria-hidden="true">1</span>行く場所</li><li><span class="outing-step-number" aria-hidden="true">2</span>往復・費用</li><li><span class="outing-step-number" aria-hidden="true">3</span>困ったとき</li></ol>
<form id="outing-form" autocomplete="off">
<section class="outing-step" data-step="0" aria-labelledby="outing-step-0">
  <h2 class="outing-step-title" id="outing-step-0" tabindex="-1">車なしで行ってみたい場所は？</h2>
  <p class="outing-note">「いつもの内科」「駅前のスーパー」など、生活に必要な場所からひとつ選びましょう。返納するか決まっていなくても使えます。</p>
  <p id="outing-inherited-region" class="outing-note" hidden></p>
  <fieldset class="outing-purpose"><legend>どんな用事ですか？</legend><div class="outing-choices">
    <label><input type="radio" name="purpose" value="買い物"><span>買い物<small>荷物のある帰りも考える</small></span></label>
    <label><input type="radio" name="purpose" value="通院"><span>通院<small>診察が長引く日も考える</small></span></label>
    <label><input type="radio" name="purpose" value="趣味・人に会う"><span>趣味・人に会う<small>続けたい外出を考える</small></span></label>
    <label><input type="radio" name="purpose" value="その他"><span>その他<small>役所や銀行などへ</small></span></label>
  </div></fieldset>
  <label class="outing-field">具体的に行きたい場所<input id="outing-place" type="text" maxlength="80" placeholder="例：かかりつけの○○内科" aria-describedby="outing-place-help"></label>
  <p id="outing-place-help" class="outing-note">正式な施設名や住所は不要。「いつもの病院」でも始められます。</p>
  <p id="outing-purpose-hint" class="outing-scenario-hint" role="status">用事を選ぶと、その外出で考えたいことが表示されます。</p>
  <details class="outing-optional"><summary>曜日・到着したい時間も決まっている場合</summary><label class="outing-field">利用する日・時間の目安（任意）<input id="outing-day" type="text" maxlength="60" placeholder="例：平日の午前、火曜10時の診察"></label><p class="outing-note">まだ決めなくても進めます。曜日や時間で使える便が変わるため、分かったら書き足しましょう。</p></details>
  <div class="outing-actions"><button type="button" class="outing-primary" data-next>この場所への往復を考える →</button></div>
</section>
<section class="outing-step" data-step="1" aria-labelledby="outing-step-1" hidden>
  <h2 class="outing-step-title" id="outing-step-1" tabindex="-1">どうやって行って、帰りますか？</h2>
  <p id="outing-trip-context" class="outing-trip-context"></p>
  <p id="outing-trip-hint" class="outing-note"></p>
  <details class="outing-local" id="outing-local-disclosure"><summary>バス助成・タクシー支援も調べる（任意）</summary>
  <section aria-labelledby="outing-local-title">
    <h3 id="outing-local-title">住んでいる市町村を選ぶ</h3>
    <p class="outing-note">行き先の地域ではなく、本人がお住まいの地域を選びます。対象条件を確かめ、今回の往復に使う支援を選べます。</p>
    <div class="outing-picked"><p id="outing-picker-summary" tabindex="-1">地域はまだ選んでいません</p><button type="button" id="outing-picker-toggle" class="outing-secondary" aria-expanded="true" aria-controls="outing-picker-body" hidden>地域を変更</button><button type="button" id="outing-picker-clear" class="outing-secondary" hidden>選択を解除</button></div>
    <div id="outing-picker-body">
      <h4>地方から都道府県を選ぶ</h4>
      <div id="outing-region-options" class="outing-region-buttons" aria-label="地方"></div>
      <div id="outing-pref-options" class="outing-place-buttons" aria-label="都道府県"></div>
      <section id="outing-city-picker" hidden aria-labelledby="outing-city-picker-title">
        <h4 id="outing-city-picker-title">市町村を選ぶ</h4>
        <label class="outing-field">市町村名で絞り込む<input id="outing-city-search" type="search" maxlength="40" placeholder="例：西宮、にしのみや" aria-describedby="outing-city-search-help" disabled></label>
        <p id="outing-city-search-help" class="outing-note">漢字・ひらがな・カタカナで探せます。</p>
        <div id="outing-city-initials" class="outing-kana-buttons" aria-label="市町村の頭文字"></div>
        <p id="outing-city-count" class="outing-note" role="status" tabindex="-1"></p>
        <div id="outing-city-results" class="outing-place-buttons" aria-label="市町村の候補"></div>
        <div class="outing-city-pages"><button type="button" id="outing-city-prev" class="outing-secondary" hidden>← 前の12件</button><button type="button" id="outing-city-more" class="outing-secondary" hidden>次の12件 →</button><button type="button" id="outing-city-reset" class="outing-secondary" hidden>絞り込みを解除</button></div>
      </section>
    </div>
    <select id="outing-pref" hidden aria-hidden="true" tabindex="-1" disabled><option value="">読み込み中…</option></select><select id="outing-city" hidden aria-hidden="true" tabindex="-1" disabled><option value="">都道府県を選んでください</option></select>
    <p id="outing-support-status" class="outing-note" role="status"></p><button type="button" id="outing-support-retry" class="outing-secondary" hidden>支援情報を読み直す</button>
    <div id="outing-support-area" hidden>
      <div class="outing-local-heading"><h4>計画に入れて考える支援</h4><a id="outing-city-link" target="_blank" rel="noopener">地域の詳しい条件 ↗</a></div>
      <p class="outing-note">対象者と使える交通を確認して選びます。選ぶだけでは利用資格の判定や割引計算はしません。</p>
      <div id="outing-support-list"></div>
    </div>
  </section>
  </details>
  <p class="outing-note">交通費は1人・片道分。支援を使う場合は、自分で確かめた支払額を入力します。無料と確認できたら「0」を入れてください。</p>
  <p class="outing-note" id="outing-normal-help" hidden>通常の費用も、同じ交通・区間・条件で確かめた金額を入力します。</p>
  <div class="outing-legs">__LEGS__</div>
  <div id="outing-combination" class="outing-caution" hidden><strong>別の支援を行き・帰りに使う計画です</strong><p>片道ずつでも、同時に利用・交付を受けられない制度があります。</p><label class="outing-check-label"><input type="checkbox" id="outing-combination-confirmed"><span>この2つの支援を併用できる条件を窓口で確認した</span></label><p class="outing-note">未確認の間は、往復の支援利用後の合計を出しません。</p></div>
  <details class="outing-monthly">
    <summary id="outing-monthly-title">通い続けた場合の月額も見る（任意）</summary>
    <label class="outing-field">同じ往復のお出かけ回数（月）<input id="outing-monthly-trips" type="number" min="1" max="100" step="1" inputmode="numeric" placeholder="例：4" aria-describedby="outing-monthly-help"></label>
    <p class="outing-note" id="outing-monthly-help">1回は「行き＋帰り」。同じ交通・料金で出かける回数です。月額を比べない場合は空欄で進めます。</p>
    <label class="outing-check-label" id="outing-monthly-confirmed-wrap" hidden><input type="checkbox" id="outing-monthly-confirmed"><span>この回数すべてで支援を使えることを、券の残数・利用上限・有効期限まで確認した</span></label>
    <p class="outing-note" id="outing-monthly-limit-help" hidden>申請前は、交付後の想定で確認します。未確認の間は、支援利用後の月額を出しません。</p>
  </details>
  <section id="outing-comparison-preview" class="outing-comparison" aria-label="入力した交通費の比較"></section>
  <p class="outing-note">運行日・帰りの便・予約の要否は、利用する交通の公式案内で確認しましょう。</p>
  <div class="outing-actions"><button type="button" class="outing-secondary" data-back>← 行く場所へ</button><button type="button" class="outing-primary" data-next>困ったときの方法を考える →</button></div>
</section>
<section class="outing-step" data-step="2" aria-labelledby="outing-step-2" hidden>
  <h2 class="outing-step-title" id="outing-step-2" tabindex="-1">帰れない・困った、を減らすには？</h2>
  <p class="outing-note">予定どおりにいかないときの方法をひとつ考えておくと、本人も家族も相談しやすくなります。未定のままでもまとめられます。</p>
  <label class="outing-field">行きと帰りの予約・送迎のお願い<select id="outing-booking" aria-describedby="outing-booking-help"><option>まだ未確認</option><option>どちらも予約不要</option><option>手配が残っている</option><option>すべて手配済み</option></select></label>
  <p class="outing-note" id="outing-booking-help">片道でも未確認・未手配なら、「まだ未確認」か「手配が残っている」を選びます。送迎を頼む相手にも確認しましょう。</p>
  <label class="outing-field">雨の日・便に間に合わないときは？<textarea id="outing-backup" maxlength="240" rows="2" placeholder="別の便を調べる、タクシーを確認するなど"></textarea></label>
  <label class="outing-field">持ち物・気になること<textarea id="outing-note" maxlength="300" rows="2" placeholder="荷物が多い日の帰り方、バス停までの歩きやすさなど"></textarea></label>
  <div class="outing-actions"><button type="button" class="outing-secondary" data-back>← 行きと帰りへ</button><button type="button" class="outing-primary" id="outing-finish">検討結果と、次に調べることを見る →</button></div>
</section>
</form>
<section class="outing-result" id="outing-result" aria-labelledby="outing-result-title" hidden>
  <div class="outing-ticket"><header><p class="outing-kicker">本人・家族で見返す、往復の検討メモ</p><h2 id="outing-result-title" tabindex="-1">この場所へ通うために、分かったこと。</h2><p id="outing-result-destination"></p></header>
  <p class="outing-summary-route" id="outing-result-route"></p>
  <section class="outing-next-action" aria-labelledby="outing-next-title"><h3 id="outing-next-title">まず、ここを確認しましょう</h3><p id="outing-result-next"></p></section>
  <div id="outing-result-overview" class="outing-overview" aria-label="入力した内容の整理"></div>
  <section id="outing-result-comparison" class="outing-comparison" aria-label="交通費の比較" hidden></section>
  <div class="outing-result-grid" id="outing-result-details"></div>
  <section id="outing-result-supports" class="outing-result-supports" hidden></section>
  <section><h3>調べること・出発前に確かめること</h3><ul class="outing-checks" id="outing-result-checks"></ul></section>
  <p class="outing-note">このメモは入力内容をまとめたものです。運行・予約・運賃は、利用前に公式案内で確かめてください。</p>
  <p class="outing-note">じもとくらべ · https://jimotokurabe.jp/outing-plan.html</p></div>
  <div class="outing-actions"><button type="button" class="outing-primary" id="outing-copy">検討メモをコピー</button><button type="button" class="outing-secondary" id="outing-print" data-print>検討メモを印刷</button><button type="button" class="outing-secondary" id="outing-edit">内容を直す</button></div>
  <p class="outing-status" id="outing-status" role="status"></p>
  <details class="outing-memo"><summary>コピー用の文章を見る</summary><textarea id="outing-memo" rows="12" readonly aria-label="コピー用の計画"></textarea></details>
</section>
</div>
<p class="outing-note outing-privacy">行き先・日時・費用などの計画入力は送信・保存されません。選んだ都道府県の公開制度データを読み込みます。ページを再読み込みすると消えるため、必要な計画はコピーか印刷で残してください。</p>
</div>
<aside class="outing-help" aria-labelledby="outing-help-title"><h2 id="outing-help-title">こんな検討に使えます</h2><details class="outing-use-example" open><summary>いつもの病院へ通いたい</summary><p><strong>行きはバス。帰りは診察次第。</strong></p><p>帰りの便があるか、タクシーならいくらか。地元の支援が使えるかも確認して、家族と相談するメモに。</p><p class="outing-note">使い方の例です。実際の経路・料金はご自身で調べて入力します。</p></details><details><summary>買い物を続けたい</summary><p>行きは歩けても、帰りは荷物が心配。帰りだけバスやタクシーにした場合の方法・費用を整理します。</p></details><details><summary>家族と一度試したい</summary><p>車を使わない日を一度つくり、乗り場までの道や帰り方を一緒に確認。日付は話し合ってから決められます。</p></details><div class="outing-links"><a href="index.html#prefectures" target="_blank" rel="noopener">地域の交通・支援を探す ↗</a><a href="henno-hanashikata.html" target="_blank" rel="noopener">家族へのひと言を考える ↗</a></div><p class="outing-note">別のタブで開きます。計画の入力を残したまま調べられます。</p><details><summary>計画を立てる小さなヒント</summary><p>まずは行き慣れた場所をひとつ。家から乗り場まで、降りてから目的地までの道も確認しましょう。</p><p>帰りの時間が読めない日は、次の便や別の交通も調べておくと相談しやすくなります。</p></details><details><summary>このページについて</summary><p>じもとくらべが作成した準備用のメモです。免許を返納するか決まっていなくても使えます。</p><p>移動を事前に試す考え方は、<a href="https://www.city.tajimi.lg.jp/kurashi_tetsuduzuki/machizukuri/1005719/1005780/1010861.html" target="_blank" rel="noopener">多治見市のおためし事業（公式・別タブ）</a>も参考にしています。自治体の割引事業への申込みではありません。</p></details></aside>
</div>'''
    legs = []
    options = ''.join(f'<option>{mode}</option>' for mode in ('まだ決めていない', 'バス', '電車', 'タクシー', '家族・知人の送迎', '徒歩', 'その他'))
    for key, label, hint in [('out', '行き', '家を出る時間など'), ('back', '帰り', '帰りの便・出発時間など')]:
        legs.append(f'''<fieldset><legend>{label}</legend>
        <label class="outing-field">{label}の交通<select id="outing-{key}-mode">{options}</select></label>
        <label class="outing-field">{label}の時間・乗り場<input id="outing-{key}-time" type="text" maxlength="120" placeholder="{hint}"></label>
        <label class="outing-field" id="outing-{key}-support-field" hidden>{label}に使う支援<select id="outing-{key}-support"><option value="">支援を指定しない</option></select></label>
        <p id="outing-{key}-support-help" class="outing-note" hidden>支援を使う場合は、この画面の「バス助成・タクシー支援も調べる」を開いてください。</p>
        <label class="outing-field" id="outing-{key}-normal-wrap" hidden>{label}の通常の交通費（円）<input id="outing-{key}-normal-cost" type="number" min="0" max="1000000" step="1" inputmode="numeric" placeholder="支援を使わない場合" aria-describedby="outing-normal-help"></label>
        <label class="outing-field"><span id="outing-{key}-cost-label">{label}の交通費（円）</span><input id="outing-{key}-cost" type="number" min="0" max="1000000" step="1" inputmode="numeric" placeholder="未確認"></label>
        <label class="outing-check-label" id="outing-{key}-confirmed-wrap" hidden><input type="checkbox" id="outing-{key}-confirmed"><span>この片道で使える条件・自己負担額を確認した</span></label>
        </fieldset>''')
    raw = shell(title='いつもの病院やお店へ車なしで通うには？｜お出かけ計画｜じもとくらべ',
                description='具体的な病院やお店への往復を、車以外の交通で検討。地元のバス助成・タクシー支援、入力した費用、次に調べることを本人や家族で整理し、コピー・印刷できます。',
                path='outing-plan.html', main=main.replace('__LEGS__', ''.join(legs)), draft=draft)
    soup = BeautifulSoup(raw, 'html.parser')
    soup.body['class'] = ['outing-page']
    soup.main['class'] = ['outing-main']
    mast = soup.select_one('.topbar')
    mast['class'] = ['mast']
    mast.select_one('.sizer')['class'] = ['size']
    for script in soup.select('script:not([src])'):
        if 'jk-size' in script.get_text():
            script.decompose()
    for link in soup.select('link[href]'):
        if 'fonts.google' in link['href']:
            link.decompose()
    boot = soup.new_tag('script')
    boot.string = "try{document.documentElement.classList.toggle('large',sessionStorage.getItem('jk-national-size')==='large')}catch(e){}"
    soup.head.append(boot)
    soup.head.append(soup.new_tag('link', rel='stylesheet', href='assets/outing-plan.css?v=20261010-purpose'))
    apply_site_header(soup)
    for src in ('assets/warm-guides.js', 'assets/outing-plan.js?v=20261010-purpose'):
        soup.body.append(soup.new_tag('script', src=src, defer=True))
    return str(soup)
