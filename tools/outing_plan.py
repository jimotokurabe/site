"""Generate the nationwide, private-by-default outing worksheet."""
from bs4 import BeautifulSoup
from site_header import apply_site_header


def outing_plan_page(shell, draft=False):
    main = '''<nav class="crumbs" aria-label="現在の場所"><a href="index.html">トップ</a> ／ お出かけ計画</nav>
<header class="outing-hero">
  <div><p class="outing-kicker">まずは、いつもの行き先をひとつ。</p>
  <h1>車なしの<br>お出かけ計画</h1>
  <p>病院へ、お店へ、会いたい人へ。<br>行きも帰りも、一緒に考えてみましょう。</p></div>
  <div class="outing-route" aria-label="家から行き先へ、帰りも家まで">
    <svg viewBox="0 0 420 150" role="img" aria-label="家・行き先・家をつなぐ往復の道">
      <path d="M70 93 Q150 15 210 93 T355 93" fill="none" stroke="#285b40" stroke-width="3" stroke-dasharray="5 7"/>
      <g stroke="#285b40" stroke-width="3" stroke-linejoin="round"><path d="M24 93V57L59 30l35 27v36z" fill="#b9ded5"/><path d="M49 93V68h20v25" fill="#fffefb"/><path d="M174 97V55h76v42z" fill="#f4d999"/><path d="M167 55l11-25h68l11 25z" fill="#edc7bc"/><path d="M204 97V69h17v28" fill="#fffefb"/><path d="M316 93V57l35-27 35 27v36z" fill="#d8e9f2"/><path d="M341 93V68h20v25" fill="#fffefb"/></g>
      <g fill="#285b40" font-size="17" text-anchor="middle"><text x="59" y="132">家</text><text x="211" y="132">行き先</text><text x="351" y="132">家</text></g>
    </svg>
  </div>
</header>
<div class="outing-layout">
<div class="outing-work">
<p class="outing-note">分からないところは空欄で大丈夫。あとで確認するメモに残せます。</p>
<noscript><p>計画をまとめるにはJavaScriptを有効にしてください。行き先・行きと帰りの交通・費用・予約・困ったときの代案を紙に書いて準備することもできます。</p></noscript>
<div id="outing-app" hidden>
<ol class="outing-progress" aria-label="計画づくりの進み具合"><li aria-current="step"><span class="outing-step-number" aria-hidden="true">1</span>地域・行き先</li><li><span class="outing-step-number" aria-hidden="true">2</span>行きと帰り</li><li><span class="outing-step-number" aria-hidden="true">3</span>準備</li></ol>
<form id="outing-form" autocomplete="off">
<section class="outing-step" data-step="0" aria-labelledby="outing-step-0">
  <h2 class="outing-step-title" id="outing-step-0" tabindex="-1">地元の支援も、計画に。</h2>
  <section class="outing-local" aria-labelledby="outing-local-title">
    <h3 id="outing-local-title">住んでいる市町村を選ぶ</h3>
    <p class="outing-note">お出かけする本人の地域です。支援を選ばずに進めることもできます。</p>
    <div class="outing-region-fields"><label class="outing-field">都道府県<select id="outing-pref" disabled><option value="">読み込み中…</option></select></label><label class="outing-field">市町村<select id="outing-city" disabled><option value="">都道府県を選んでください</option></select></label></div>
    <p id="outing-support-status" class="outing-note" role="status"></p><button type="button" id="outing-support-retry" class="outing-secondary" hidden>支援情報を読み直す</button>
    <div id="outing-support-area" hidden>
      <div class="outing-local-heading"><h4>計画に入れて考える支援</h4><a id="outing-city-link" target="_blank" rel="noopener">地域の詳しい条件 ↗</a></div>
      <p class="outing-note">対象者と使える交通を確認して選びます。選ぶだけでは利用資格の判定や割引計算はしません。</p>
      <div id="outing-support-list"></div>
    </div>
  </section>
  <h3>どこへ出かけますか？</h3>
  <fieldset class="outing-purpose"><legend>お出かけの目的</legend><div class="outing-choices">
    <label><input type="radio" name="purpose" value="買い物"><span>買い物</span></label>
    <label><input type="radio" name="purpose" value="通院"><span>通院</span></label>
    <label><input type="radio" name="purpose" value="趣味・人に会う"><span>趣味・人に会う</span></label>
    <label><input type="radio" name="purpose" value="その他"><span>その他</span></label>
  </div></fieldset>
  <div class="outing-fields"><label class="outing-field">行き先<input id="outing-place" type="text" maxlength="80" placeholder="いつものお店など"></label>
  <label class="outing-field">出かける日・曜日<input id="outing-day" type="text" maxlength="60" placeholder="来週の火曜日など"></label></div>
  <div class="outing-actions"><button type="button" class="outing-primary" data-next>行きと帰りを考える →</button></div>
</section>
<section class="outing-step" data-step="1" aria-labelledby="outing-step-1" hidden>
  <h2 class="outing-step-title" id="outing-step-1" tabindex="-1">行きも、帰りも。</h2>
  <p class="outing-note">交通費は1人・片道分。支援を使う場合は、自分で確かめた支払額を入力します。無料と確認できたら「0」を入れてください。</p>
  <p class="outing-note" id="outing-normal-help">通常の費用も、同じ交通・区間・条件で確かめた金額を入力します。</p>
  <div class="outing-legs">__LEGS__</div>
  <div id="outing-combination" class="outing-caution" hidden><strong>別の支援を行き・帰りに使う計画です</strong><p>片道ずつでも、同時に利用・交付を受けられない制度があります。</p><label class="outing-check-label"><input type="checkbox" id="outing-combination-confirmed"><span>この2つの支援を併用できる条件を窓口で確認した</span></label><p class="outing-note">未確認の間は、往復の支援利用後の合計を出しません。</p></div>
  <section class="outing-monthly" aria-labelledby="outing-monthly-title">
    <h3 id="outing-monthly-title">月に何回、出かけますか？</h3>
    <label class="outing-field">同じ往復のお出かけ回数（月）<input id="outing-monthly-trips" type="number" min="1" max="100" step="1" inputmode="numeric" placeholder="例：4" aria-describedby="outing-monthly-help"></label>
    <p class="outing-note" id="outing-monthly-help">1回は「行き＋帰り」。同じ交通・料金で出かける回数です。月額を比べない場合は空欄で進めます。</p>
    <label class="outing-check-label" id="outing-monthly-confirmed-wrap" hidden><input type="checkbox" id="outing-monthly-confirmed"><span>この回数すべてで支援を使えることを、券の残数・利用上限・有効期限まで確認した</span></label>
    <p class="outing-note" id="outing-monthly-limit-help" hidden>申請前は、交付後の想定で確認します。未確認の間は、支援利用後の月額を出しません。</p>
  </section>
  <section id="outing-comparison-preview" class="outing-comparison" aria-label="入力した交通費の比較"></section>
  <p class="outing-note">運行日・帰りの便・予約の要否は、利用する交通の公式案内で確認しましょう。</p>
  <div class="outing-actions"><button type="button" class="outing-secondary" data-back>← 地域・行き先へ</button><button type="button" class="outing-primary" data-next>準備を確認する →</button></div>
</section>
<section class="outing-step" data-step="2" aria-labelledby="outing-step-2" hidden>
  <h2 class="outing-step-title" id="outing-step-2" tabindex="-1">出かける前に、もう少し。</h2>
  <label class="outing-field">行きと帰りの予約・送迎のお願い<select id="outing-booking" aria-describedby="outing-booking-help"><option>まだ未確認</option><option>どちらも予約不要</option><option>手配が残っている</option><option>すべて手配済み</option></select></label>
  <p class="outing-note" id="outing-booking-help">片道でも未確認・未手配なら、「まだ未確認」か「手配が残っている」を選びます。送迎を頼む相手にも確認しましょう。</p>
  <label class="outing-field">雨の日・便に間に合わないときは？<textarea id="outing-backup" maxlength="240" rows="2" placeholder="別の便を調べる、タクシーを確認するなど"></textarea></label>
  <label class="outing-field">持ち物・気になること<textarea id="outing-note" maxlength="300" rows="2" placeholder="荷物が多い日の帰り方、バス停までの歩きやすさなど"></textarea></label>
  <div class="outing-actions"><button type="button" class="outing-secondary" data-back>← 行きと帰りへ</button><button type="button" class="outing-primary" id="outing-finish">計画をまとめる →</button></div>
</section>
</form>
<section class="outing-result" id="outing-result" aria-labelledby="outing-result-title" hidden>
  <div class="outing-ticket"><header><p class="outing-kicker">家族と確認する、お出かけメモ</p><h2 id="outing-result-title" tabindex="-1">ひとつの外出から、試してみよう。</h2><p id="outing-result-destination"></p></header>
  <p class="outing-summary-route" id="outing-result-route"></p>
  <section id="outing-result-comparison" class="outing-comparison" aria-label="交通費の比較" hidden></section>
  <div class="outing-result-grid" id="outing-result-details"></div>
  <section id="outing-result-supports" class="outing-result-supports" hidden></section>
  <section><h3>あとで確認すること</h3><ul class="outing-checks" id="outing-result-checks"></ul></section>
  <p class="outing-note">このメモは入力内容をまとめたものです。運行・予約・運賃は、利用前に公式案内で確かめてください。</p>
  <p class="outing-note">じもとくらべ · https://jimotokurabe.jp/outing-plan.html</p></div>
  <div class="outing-actions"><button type="button" class="outing-primary" id="outing-copy">計画をコピー</button><button type="button" class="outing-secondary" id="outing-print" data-print>計画を印刷</button><button type="button" class="outing-secondary" id="outing-edit">内容を直す</button></div>
  <p class="outing-status" id="outing-status" role="status"></p>
  <details class="outing-memo"><summary>コピー用の文章を見る</summary><textarea id="outing-memo" rows="12" readonly aria-label="コピー用の計画"></textarea></details>
</section>
</div>
<p class="outing-note outing-privacy">行き先・日時・費用などの計画入力は送信・保存されません。選んだ都道府県の公開制度データを読み込みます。ページを再読み込みすると消えるため、必要な計画はコピーか印刷で残してください。</p>
</div>
<aside class="outing-help" aria-labelledby="outing-help-title"><h2 id="outing-help-title">調べたいときは</h2><div class="outing-links"><a href="index.html#prefectures" target="_blank" rel="noopener">地域の交通・支援を探す ↗</a><a href="henno-hanashikata.html" target="_blank" rel="noopener">家族へのひと言を考える ↗</a></div><p class="outing-note">別のタブで開きます。計画の入力を残したまま調べられます。</p><details><summary>計画を立てる小さなヒント</summary><p>まずは行き慣れた場所をひとつ。家から乗り場まで、降りてから目的地までの道も確認しましょう。</p><p>帰りの時間が読めない日は、次の便や別の交通も調べておくと相談しやすくなります。</p></details><details><summary>このページについて</summary><p>じもとくらべが作成した準備用のメモです。免許を返納するか決まっていなくても使えます。</p><p>移動を事前に試す考え方は、<a href="https://www.city.tajimi.lg.jp/kurashi_tetsuduzuki/machizukuri/1005719/1005780/1010861.html" target="_blank" rel="noopener">多治見市のおためし事業（公式・別タブ）</a>も参考にしています。自治体の割引事業への申込みではありません。</p></details></aside>
</div>'''
    legs = []
    options = ''.join(f'<option>{mode}</option>' for mode in ('まだ決めていない', 'バス', '電車', 'タクシー', '家族・知人の送迎', '徒歩', 'その他'))
    for key, label, hint in [('out', '行き', '家を出る時間など'), ('back', '帰り', '帰りの便・出発時間など')]:
        legs.append(f'''<fieldset><legend>{label}</legend>
        <label class="outing-field">{label}の交通<select id="outing-{key}-mode">{options}</select></label>
        <label class="outing-field">{label}の時間・乗り場<input id="outing-{key}-time" type="text" maxlength="120" placeholder="{hint}"></label>
        <label class="outing-field">{label}に使う支援<select id="outing-{key}-support"><option value="">支援を指定しない</option></select></label>
        <p id="outing-{key}-support-help" class="outing-note">支援を使う場合は、最初の画面で選べます。</p>
        <label class="outing-field" id="outing-{key}-normal-wrap" hidden>{label}の通常の交通費（円）<input id="outing-{key}-normal-cost" type="number" min="0" max="1000000" step="1" inputmode="numeric" placeholder="支援を使わない場合" aria-describedby="outing-normal-help"></label>
        <label class="outing-field"><span id="outing-{key}-cost-label">{label}の交通費（円）</span><input id="outing-{key}-cost" type="number" min="0" max="1000000" step="1" inputmode="numeric" placeholder="未確認"></label>
        <label class="outing-check-label" id="outing-{key}-confirmed-wrap" hidden><input type="checkbox" id="outing-{key}-confirmed"><span>この片道で使える条件・自己負担額を確認した</span></label>
        </fieldset>''')
    raw = shell(title='車なしのお出かけ計画｜行き帰りと費用を家族で確認｜じもとくらべ',
                description='通院・買い物・趣味のお出かけを、車以外の交通で考える無料の準備メモ。行き帰り・交通費・予約・雨の日の代案をまとめてコピー・印刷できます。',
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
    soup.head.append(soup.new_tag('link', rel='stylesheet', href='assets/outing-plan.css?v=20261009-comparison'))
    apply_site_header(soup)
    for src in ('assets/warm-guides.js', 'assets/outing-plan.js?v=20261009-comparison'):
        soup.body.append(soup.new_tag('script', src=src, defer=True))
    return str(soup)
