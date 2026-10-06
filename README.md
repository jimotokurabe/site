# じもとくらべ

https://jimotokurabe.jp/

市や町ごとにちがう制度を、公式ページで確かめて、同じ項目にそろえて比べるサイトです。
GitHub Pages（main ブランチの直下）で公開しています。

## ファイル

| ファイル | 中身 |
|---|---|
| `data/hyogo-menkyo-henno.json` | 兵庫県41市町の免許返納特典のデータ（ページの元）。`common` は県内共通の手続き、各市町の `guide` は手順ページの中身 |
| `data/hyogo-taxi.json` | 41市町の高齢者のタクシー代の助成のデータ。返納特典の一覧の、市町ごとの欄の下に出る |
| `data/<県>-bus.json`、`BUS.md` | 高齢者バス助成・敬老パスの比較データと全国展開手順。兵庫県41市町から開始。`draft: true` の間は確認用の下書き |
| `tools/bus_pages.py`、`tools/validate_bus.py`、`tools/verify_bus_evidence.py` | バス比較の画面生成、全市町村と必須項目の検証、非公開の根拠原文の照合 |
| `data/<県>-menkyo-henno.json` の `pref` | 県の名前・単位（市町／市町村）・県内共通の割引。`draft: true` の県は下書き（検索に出さず、サイトマップにも載せない）。ほかの県も同じ形のファイルを置けば、`<県>-menkyo-henno.html`・`<県>-taxi.html` ができる |
| `tools/check_quotes.py` | 調べたときの抜き書きが、いまの公式ページに載っているかを確かめる |
| `data/hanashikata.json` | 「親に運転の話をはじめる、最初のひと言」（`henno-hanashikata.html`）の質問・タイプ・ひと言の例と、出典（警察庁の返納件数・支援マニュアル・#8080）。ひと言はサイトが書いた例で、事実ではない。数字と出典は確かめた日を `checked` に書く |
| `tools/build.py` | データからページを作るスクリプト |
| `tools/check_guide.js`、`tools/check_links.py` | 手順ページをブラウザで開いて確かめる道具と、ページのリンクが開けるかを確かめる道具 |
| `GUIDES.md` | 手順ページを作る順番と作り方 |
| `TOPICS.md` | 新しい制度のページを作る順番と作り方 |
| `site.css` | 全ページ共通の見た目 |
| `index.html` ほか `*.html`、`hyogo-menkyo-henno/*.html`、`sitemap.xml`、`robots.txt` | `tools/build.py` が作るもの。手で直さない |
| `CNAME`、`.nojekyll` | 独自ドメインの設定と、ファイルをそのまま公開する設定 |

## 更新のしかた

1. `data/hyogo-menkyo-henno.json` か `data/hyogo-taxi.json` を直す（確かめた日は `checked`）
2. `python3 tools/build.py` でページを作り直す
3. 生成されたファイルも含めて main に push する（数分で本番に出る）
