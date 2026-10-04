# 全国の移動案内データ

`mobility.html` は `tools/build.py` が生成する全国の入口です。市区町村は既存の `data/<県>-menkyo-henno.json` と `data/<県>-taxi.json` から生成し、公開用の `mobility-city-index.json` にまとめます。元の市区町村名・よみ・助成分類・調査日・既存ページへのリンクを使います。確認済みの東播磨と周辺9地域には、検索から直接開ける `hyogo-mobility/<地域ID>.html` も生成します。

## 識別子

全国では `slug` が重複するため、県IDと市区町村slugの組を主キーとします。詳細案内の掲載範囲は `data/mobility-coverage.json` の `entries` に別に記録します。神戸市西区の案内は、神戸市全域の詳細案内として扱いません。

## 詳細案内の登録

`entries` の項目：

| 項目 | 意味 |
|---|---|
| `pref` | 既存データの県ID |
| `municipality` | 県内の市区町村slug |
| `scope` | 実際に確認した地域の表示名 |
| `page` | サイト内の地域別ページ。全国検索からここへ直接リンクする |
| `city` | `data/east-harima-mobility.json` の地域ID |
| `level` | `detailed`（その市区町村の案内）または `partial`（地区限定の案内） |

新しい地域交通を追加するときは、自治体・交通事業者の公式情報で運行区域、予約、運行日、費用、対象者、実証や終了の期限を確認し、出典と確認日を詳細案内の元データに記録します。その後、この対応表に詳細案内の入口を登録します。今ある9地域は、地域別ページと、目的別に絞れる `east-harima-mobility.html` の両方へリンクします。神戸市西区は一部地区だけの案内で、西区全域の交通を網羅しません。助成データの `notfound` は「交通手段なし」の意味ではありません。

検索用JSONとHTMLは手で編集せず `python3 tools/build.py` で更新します。
