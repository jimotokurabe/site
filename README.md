# じもとくらべ

https://jimotokurabe.jp/

市や町ごとにちがう制度を、公式ページで確かめて、同じ項目にそろえて比べるサイトです。
GitHub Pages（main ブランチの直下）で公開しています。

## ファイル

| ファイル | 中身 |
|---|---|
| `data/hyogo-menkyo-henno.json` | 兵庫県41市町の免許返納特典のデータ（ページの元） |
| `tools/build.py` | データからページを作るスクリプト |
| `site.css` | 全ページ共通の見た目 |
| `index.html` ほか `*.html`、`sitemap.xml`、`robots.txt` | `tools/build.py` が作るもの。手で直さない |
| `CNAME`、`.nojekyll` | 独自ドメインの設定と、ファイルをそのまま公開する設定 |

## 更新のしかた

1. `data/hyogo-menkyo-henno.json` を直す（確かめた日は `checked`）
2. `python3 tools/build.py` でページを作り直す
3. 生成されたファイルも含めて main に push する（数分で本番に出る）
