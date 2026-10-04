# 全国の移動案内データ

`mobility.html` は `tools/build.py` が生成する全国の入口です。市区町村は既存の `data/<県>-menkyo-henno.json` と `data/<県>-taxi.json` から生成し、公開用の `mobility-city-index.json` にまとめます。元の市区町村名・よみ・助成分類・調査日・既存ページへのリンクを使います。確認済みの東播磨と周辺9地域は `hyogo-mobility/<地域ID>.html`、新たに確認した東京・千葉・大阪の17地域は `<県ID>-mobility/<市区町村slug>.html` を検索から直接開けます。

トップの「移動手段を探す」と「制度から探す」は同じ都道府県・市区町村選択へ進みます。詳細案内がある地域は交通・助成・返納を見渡せる地域別ページへ進み、交通の詳細が未調査の自治体は `mobility.html?pref=<県ID>&city=<slug>` で掲載状況と既存の助成・返納情報を示します。市区町村ごとの交通情報を確認してから、対応表へ登録し、地域別ページを増やします。

## 識別子

全国では `slug` が重複するため、県IDと市区町村slugの組を主キーとします。兵庫の既存詳細案内は `data/mobility-coverage.json`、全国へ追加する個別案内は `data/municipal-mobility.json` に掲載範囲を記録します。生成時に両者を合わせて検索索引にします。神戸市西区や他の地区限定案内は、市区町村全域の案内として扱いません。

## 詳細案内の登録

`entries` の項目：

| 項目 | 意味 |
|---|---|
| `pref` | 既存データの県ID |
| `municipality` | 県内の市区町村slug |
| `scope` | 実際に確認した地域の表示名 |
| `page` | サイト内の地域別ページ。全国検索からここへ直接リンクする |
| `city` | 兵庫の既存案内では地域ID。全国向け個別案内では「県ID:市区町村slug」 |
| `level` | `detailed`（その市区町村の案内）または `partial`（地区限定の案内） |

新しい地域交通を追加するときは、自治体・交通事業者の公式情報で運行区域、予約、運行日、費用、対象者、実証や終了の期限を確認し、出典と確認日を詳細案内の元データに記録します。全国向け個別案内は `data/municipal-mobility.json` の `cities` に1市区町村ずつ追加し、`level` を `detailed` または `partial` にします。`partial` のときは対象地区を `scope` と `quick_scope` に明記します。兵庫の既存9地域は、地域別ページと、目的別に絞れる `east-harima-mobility.html` の両方へリンクします。助成データの `notfound` は「交通手段なし」の意味ではありません。

検索用JSONとHTMLは手で編集せず `python3 tools/build.py` で更新します。
