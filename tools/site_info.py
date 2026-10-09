"""Current service information and privacy disclosures, in the shared warm UI."""
from bs4 import BeautifulSoup
from site_header import apply_site_header

ICONS = {
    'place': '<path d="M25 13c0 8-9 15-9 15S7 21 7 13a9 9 0 1 1 18 0Z"/><circle cx="16" cy="13" r="3"/>',
    'talk': '<path d="M5 5h22v16H14l-7 6v-6H5Z"/><path d="M10 11h12M10 16h8"/>',
    'route': '<circle cx="7" cy="7" r="3"/><circle cx="25" cy="25" r="3"/><path d="M10 7h9a6 6 0 0 1 0 12h-6a6 6 0 0 0 0 12M22 25h-6"/>',
    'note': '<rect x="7" y="3" width="18" height="26" rx="3"/><path d="M12 10h8M12 16h8M12 22h5"/>',
    'device': '<rect x="3" y="5" width="26" height="18" rx="3"/><path d="M11 28h10M16 23v5M11 14l3 3 7-7"/>',
    'chart': '<path d="M5 4v24h24M11 22v-7M18 22V9M25 22V4"/>',
}


def cards(items):
    return '<nav class="info-cards" aria-label="このページの要点">' + ''.join(
        f'<a href="{href}"><svg viewBox="0 0 32 32" aria-hidden="true">{ICONS[icon]}</svg><span><strong>{title}</strong><small>{body}</small></span><span class="info-arrow" aria-hidden="true">{"↓" if href.startswith("#") else "→"}</span></a>'
        for icon, title, body, href in items) + '</nav>'


def about_content(contact):
    return f'''<header class="info-hero">
<p class="info-eyebrow">じもとくらべについて</p><h1>運営者情報</h1>
<p class="info-lead">住み慣れたまちで、<br>これからの移動を考えるために。</p>
<p>免許返納の前も、車を使わない日も。<br>地域の支援を調べ、本人と家族で次の一歩を考えるサイトです。</p>
</header>
{cards([('place', '地域の支援を探す', '返納特典・バス助成・タクシー支援', 'index.html#prefectures'), ('talk', '家族と話し始める', '話の切り出し方や、ひと言の例', 'henno-hanashikata.html'), ('route', '車なしの往復を考える', 'いつもの病院・お店への方法と費用', 'outing-plan.html')])}
<div class="info-layout"><div class="info-body">
<section id="editorial"><h2>情報をどう確かめるか</h2>
<p>自治体・警察・交通事業者などの公式情報をもとに、対象者・支援内容・申請先を整理しています。</p>
<ul class="info-principles"><li><strong>出典と確認日を添える</strong><span>ご自身でも元の案内を確認できるようにします。</span></li><li><strong>分からないことは、そのまま伝える</strong><span>記載なし・要確認・終了を区別し、推測で補いません。</span></li><li><strong>制度の条件を省かない</strong><span>年齢や居住地、返納の要否などを合わせて案内します。</span></li></ul>
<p class="info-note">画面のデザイン変更だけで、制度の確認日を更新することはありません。</p></section>
<section id="use"><h2>利用するときに知っておいてほしいこと</h2>
<p>個人が運営する情報サイトで、自治体や交通事業者の公式サイトではありません。制度への申請や交通の予約は、各窓口で行ってください。</p>
<p>掲載内容は確認日時点の情報です。対象になるか、今も利用できるかは、申し込み前に公式ページや窓口で確かめてください。</p>
<p>会話のひと言は、このサイトが作成した例です。お出かけ計画は入力した方法・費用を整理する道具で、経路・運賃や利用資格を自動で調べるものではありません。</p>
<p class="info-note">このサイトの情報の利用により生じた損害について、責任を負いかねます。</p></section>
<section id="ads"><h2>広告について</h2><p>現在、広告は掲載していません。掲載する場合も、広告の都合で制度の内容を変えることはしません。</p></section>
</div><aside class="info-aside" aria-label="運営と連絡先">
<section class="info-profile"><p class="info-eyebrow">運営の基本情報</p><h2>じもとくらべ</h2><dl><div><dt>運営形態</dt><dd>個人運営</dd></div><div><dt>サイト</dt><dd><a href="https://jimotokurabe.jp/">jimotokurabe.jp</a></dd></div></dl><a href="privacy.html">プライバシーポリシー →</a></section>
<section class="info-contact" id="contact"><h2>間違い・変更のお知らせ</h2><p>地域名、該当ページ、気づいた内容をお知らせください。公式情報を確認して修正します。</p><a class="info-button" href="{contact}" target="_blank" rel="noopener">お問い合わせ ↗</a><p class="info-note">Googleフォームが開きます。制度の申請・利用可否の相談は、各制度の窓口へお願いします。</p></section>
</aside></div><p class="info-updated">2026年9月26日 作成 ／ 2026年10月10日 更新</p>'''


def privacy_content(contact):
    return f'''<header class="info-hero">
<p class="info-eyebrow">安心して使うために</p><h1>プライバシー<wbr>ポリシー</h1>
<p class="info-lead">入力したこと、保存すること。</p>
<p>じもとくらべで扱う情報を、機能ごとに説明します。<br>会員登録は不要です。お問い合わせは外部のフォームで受け付けています。</p>
</header>
{cards([('note', 'お出かけ計画の入力', '行き先・日時・費用は画面内で処理', '#inputs'), ('device', 'ブラウザに残るもの', '確認チェック・表示設定など', '#storage'), ('chart', '外部に送るもの', 'アクセス解析・お問い合わせなど', '#analytics')])}
<div class="info-layout"><div class="info-body">
<section id="inputs"><h2>入力内容と、コピー・共有</h2>
<p><strong>お出かけ計画の行き先・日時・費用・メモは、画面内で処理します。</strong>サイトの機能として保存したり、運営者へ送信したりする処理はありません。再読み込みすると消えるため、必要な内容はコピーや印刷で残してください。</p>
<p>地域を選ぶと、その都道府県の公開制度データを読み込みます。地域・制度のリンクには選択先の識別情報が含まれますが、入力した行き先や費用は含めません。</p>
<p>家族向けの質問や費用の試算も画面内で処理します。地域のページから戻ったときに結果を表示するため、一部の結果と選択地域を同じタブ内に一時保存します。</p>
<p>コピーは端末のクリップボードへ書き込みます。メッセージアプリなどへ貼り付けて送った内容や、外部サービスで共有した情報は、送信先サービスの取り扱いに従います。</p>
<p class="info-note">ページの閲覧・操作については、下記のアクセス解析が行われます。</p></section>
<section id="storage"><h2>ブラウザに保存する情報</h2>
<p>続きから確認したり、選んだ表示で読んだりできるよう、以下をブラウザ内に保存します。これらの保存情報を運営者へ送信する処理はありません。</p>
<dl class="info-storage"><div><dt>市町村ページの確認チェック</dt><dd>同じ端末・ブラウザで見直せるように保存します。</dd></div><div><dt>文字の大きさ</dt><dd>主なページでは同じタブ内で引き継ぎます。一部のページでは、ブラウザを閉じた後も設定を保存します。</dd></div><div><dt>選択した都道府県</dt><dd>一部の地域選択で、次に開くときのために保存します。</dd></div><div><dt>家族向け質問の結果・選択地域</dt><dd>地域情報から戻るときのために、同じタブ内に一時保存します。</dd></div></dl>
<p class="info-note">保存した設定やチェックは、ブラウザの設定でこのサイトのデータを削除すると消せます。削除すると、確認チェックや表示設定も初期状態に戻ります。</p></section>
<section id="analytics"><h2>アクセス解析</h2>
<p>使われ方を知り、サイトを改善するために Google アナリティクス 4 を利用しています。Cookieなどを使い、閲覧ページのURL、アクセス日時、端末・ブラウザ、参照元、ページ内の操作などの情報をGoogleへ送信します。</p>
<p>公式情報へのリンクを開く操作なども計測します。お出かけ計画の自由入力内容を、独自の計測項目として送る処理はありません。</p>
<p><a href="https://support.google.com/analytics/answer/6004245?hl=ja" target="_blank" rel="noopener">Google アナリティクスのデータの取り扱い ↗</a></p>
<p>対応するブラウザでは、<a href="https://tools.google.com/dlpage/gaoptout?hl=ja" target="_blank" rel="noopener">Google アナリティクス オプトアウト アドオン</a>で計測を無効にできます。Cookieの許可・削除はブラウザの設定でも管理できます。</p></section>
<section id="services"><h2>ページの表示に使う外部サービス</h2>
<dl class="info-storage"><div><dt>GitHub Pages</dt><dd>サイトの公開に利用しています。GitHubは、セキュリティのために訪問者のIPアドレスを記録します。<a href="https://docs.github.com/ja/pages/getting-started-with-github-pages/what-is-github-pages" target="_blank" rel="noopener">GitHubの説明 ↗</a></dd></div><div><dt>Google Fonts</dt><dd>一部のページで文字の表示に使っています。文字データを読み込む際にGoogleのサーバーへ接続し、IPアドレスなどが送られます。<a href="https://policies.google.com/privacy?hl=ja" target="_blank" rel="noopener">Googleのプライバシーポリシー ↗</a></dd></div></dl></section>
<section id="inquiries"><h2>お問い合わせの情報</h2>
<p><a href="{contact}" target="_blank" rel="noopener">お問い合わせ用のGoogleフォーム ↗</a>から送信された内容は、Googleのサーバーに保存されます。いただいた内容やメールアドレスは、お問い合わせへの対応のために使います。</p>
<p>お問い合わせ内容に関する確認・訂正・削除のご相談も、同じフォームからご連絡ください。</p></section>
<section id="changes"><h2>広告・このページの変更</h2><p>現在、広告は掲載していません。広告を始める場合は、開始前にこのページへ記載します。情報の取り扱いを変更するときは、このページと更新日を更新します。</p></section>
</div><aside class="info-aside" aria-label="ページ内の案内"><nav class="info-index" aria-label="プライバシーポリシーの目次"><p class="info-eyebrow">確認したい項目へ</p><a href="#inputs">入力・コピー・共有</a><a href="#storage">ブラウザ内の保存</a><a href="#analytics">アクセス解析</a><a href="#services">外部サービス</a><a href="#inquiries">お問い合わせの情報</a><a href="#changes">広告・変更について</a></nav><p class="info-related"><a href="about.html">運営者情報を見る →</a></p></aside></div>
<p class="info-updated">2026年10月10日 更新</p>'''


def info_page(shell, contact, draft, privacy=False):
    title = 'プライバシーポリシー' if privacy else '運営者情報'
    path = 'privacy.html' if privacy else 'about.html'
    main = f'<nav class="crumbs" aria-label="パンくず"><a href="index.html">ホーム</a> / {title}</nav><article class="site-info">' + (privacy_content(contact) if privacy else about_content(contact)) + '</article>'
    soup = BeautifulSoup(shell(title=title+'｜じもとくらべ', description=(
        '入力内容、ブラウザ内の保存、アクセス解析、お問い合わせの情報の取り扱いについて。' if privacy else
        'じもとくらべの目的、情報の確認方針、運営とお問い合わせについて。'),
        path=path, main=main, draft=draft), 'html.parser')
    soup.body['class'] = ['info-page']
    soup.select_one('.topbar')['class'] = ['mast']
    soup.select_one('.sizer')['class'] = ['size']
    for script in soup.select('script:not([src])'):
        if 'jk-size' in script.get_text():
            script.decompose()
    for link in soup.select('link[href]'):
        if 'fonts.google' in link['href']:
            link.decompose()
    boot = soup.new_tag('script')
    boot.string = "try{document.documentElement.classList.toggle('large',sessionStorage.getItem('jk-national-size')==='large')}catch(e){}"
    soup.head.append(boot)
    soup.head.append(soup.new_tag('link', rel='stylesheet', href='assets/site-info.css?v=20261010'))
    apply_site_header(soup)
    soup.body.append(soup.new_tag('script', src='assets/warm-guides.js', defer=True))
    return str(soup)
