# じもとくらべ

https://jimotokurabe.jp/

市や町ごとにちがう制度を、公式ページで確かめて、同じ項目にそろえて比べるサイトです。
GitHub Pages（main ブランチの直下）で公開しています。

## ファイル

| ファイル | 中身 |
|---|---|
| `data/hyogo-menkyo-henno.json` | 兵庫県41市町の免許返納特典のデータ（ページの元）。`common` は県内共通の手続き、各市町の `guide` は手順ページの中身 |
| `data/hyogo-taxi.json` | 41市町の高齢者のタクシー代の助成のデータ。返納特典の一覧の、市町ごとの欄の下に出る |
| `data/<県>-bus.json`、`BUS.md` | 高齢者バス助成・敬老パスの比較データと全国展開手順。兵庫・大阪・京都・奈良・滋賀・和歌山・三重・愛知・岐阜・静岡・鳥取・島根・岡山・広島・山口の15府県465市町村を2026年10月6日に公開。2026年10月7日に関東・北陸甲信13都県501自治体と九州・四国・福島12県387自治体を公開し、残り7道県388自治体も公開し、全国47都道府県1,741自治体の初回調査データを公開済み。`draft: true` の間は確認用の下書き |
| `tools/bus_pages.py`、`tools/validate_bus.py`、`tools/verify_bus_evidence.py`、`assets/bus.css` | バス比較の画面生成、全市町村と必須項目の検証、非公開の根拠原文の照合、比較ページ専用の見た目 |
| `data/<県>-menkyo-henno.json` の `pref` | 県の名前・単位（市町／市町村）・県内共通の割引。`draft: true` の県は下書き（検索に出さず、サイトマップにも載せない）。ほかの県も同じ形のファイルを置けば、`<県>-menkyo-henno.html`・`<県>-taxi.html` ができる |
| `tools/check_quotes.py` | 調べたときの抜き書きが、いまの公式ページに載っているかを確かめる |
| `data/hanashikata.json` | 「親に運転の話をはじめる、最初のひと言」（`henno-hanashikata.html`）の質問・タイプ・ひと言の例と、出典（警察庁の返納件数・支援マニュアル・#8080）。ひと言はサイトが書いた例で、事実ではない。数字と出典は確かめた日を `checked` に書く |
| `data/east-harima-mobility.json` | 東播磨5市町と周辺4市区の地域交通と運賃助成。`east-harima-mobility.html` の元データ。公式ページの確認日は `checked` に書く |
| `hyogo-mobility/*.html` | 確認済み9地域の移動手段と運賃支援を地域別にまとめたページ。`tools/build.py` から生成する |
| `data/mobility-coverage.json` | 全国検索から詳細な地域交通ページへつなぐ対応表。市区町村の一部だけを扱う場合は `partial` と対象地区を明記する |
| `data/municipal-mobility.json`、`<県ID>-mobility/*.html` | 兵庫県以外も含む市区町村別の交通・運賃支援。元データに確認日、対象地区、予約、費用、公式出典を記録し、HTMLを生成する |
| `mobility.html`、`mobility-city-index.json` | 47都道府県の市区町村から、確認済みの地域交通・タクシー助成・免許返納情報を探す入口。トップでは町名を直接入力して3種類の情報を確認でき、都道府県からも選べる。`tools/build.py` から生成する |
| `docs/mobility-data.md` | 全国検索の元データ、地域交通の掲載範囲、追加手順 |
| `menkyo-henno-guide.html` | 免許返納の基本ガイド。警察庁の全国共通の説明と、都道府県警察・市町村別ページへの入口。`tools/build.py` から生成する |
| `guide-city-data/*.json` | 基本ガイドで都道府県を選んだときに読み込む市町村データ。`tools/build.py` から生成する |
| `tools/build.py` | データからページを作るスクリプト |
| `tools/check_guide.js`、`tools/check_links.py` | 手順ページをブラウザで開いて確かめる道具と、ページのリンクが開けるかを確かめる道具 |
| `GUIDES.md` | 手順ページを作る順番と作り方 |
| `TOPICS.md` | 新しい制度のページを作る順番と作り方 |
| `site.css` | 返納詳細ページの黒基調を全ページで共用する見た目。印刷時は白地にする |
| `index.html` ほか `*.html`、`hyogo-menkyo-henno/*.html`、`sitemap.xml`、`robots.txt` | `tools/build.py` が作るもの。手で直さない |
| `CNAME`、`.nojekyll` | 独自ドメインの設定と、ファイルをそのまま公開する設定 |

## 更新のしかた

1. `data/hyogo-menkyo-henno.json` か `data/hyogo-taxi.json` を直す（確かめた日は `checked`）
2. `python3 tools/build.py` でページを作り直す
3. 生成されたファイルも含めて main に push する（数分で本番に出る）

## 全国の市町村ページ

`python3 tools/build.py` で、トップ → 都道府県 → 1741市町村のページとサイトマップを生成します。`beautifulsoup4` が必要です（`python3 -m pip install beautifulsoup4`）。確認用は `python3 tools/build.py --out preview --draft` で生成します。

`data/municipality-supplements.json` に市町村の一覧と、公式出典・原文根拠を確認して採用した補足を保存しています。既存制度の確認日と、補足情報の確認日は分けて表示します。未確認事項は未確認のまま掲載します。採用する補足には `reviewed: true` と `safety_accepted: true`、内容・出典・原文根拠が必要です。`assets/notice.css` が個別ページの表示を定義します。生成HTMLを直接編集せず、データと生成処理を更新してください。

## 市町村中心の支援案内

トップは市町村名の検索、都道府県ページは市町村を選ぶ入口です。市町村ページで免許返納特典、バス助成・敬老パス、タクシー支援、通院・買い物の交通を確認できます。

`tools/national_pages.py` が `tools/national_navigation.py`、`tools/national_city.py`、`tools/seo_content.py` を通じて47都道府県・1,741市区町村を生成します。`python3 tools/build.py` から呼び出すため、通常の更新手順で再生成できます。表示には `assets/national-city.css`、`assets/national-city.js`、`assets/seo.css` を使用します。

検索タイトルと冒頭の質問・回答は既存データから生成します。同名自治体には都道府県名を添え、終了・未発見・未掲載・要確認を区別します。金額だけを取り出さず、対象条件・期限・注意事項・出典と確認日を併記します。神戸・横浜・鹿児島の詳細レイアウトは `tools/templates/national/` のテンプレートを使うため、これらの制度データを更新した際は表示内容も照合してください。公開前の生成結果は `--out preview --draft` で確認できます。

公開前の確認：

```sh
python3 tools/build.py
python3 tools/check_publication.py
python3 tools/check_national_records.py
python3 tools/validate_bus.py
```

既存のURL・ページ内リンク、canonical、サイトマップ、計測、運営者情報とプライバシーポリシーへの導線を保持します。制度の再調査を行わない画面変更では、データの確認日を書き換えません。
