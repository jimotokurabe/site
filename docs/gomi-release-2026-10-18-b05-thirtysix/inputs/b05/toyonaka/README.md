# 豊中市 ごみ支援調査（2026-10-18）

## 判定

ふれあい収集は本人・世帯員が排出困難な世帯に、全ごみ種を決まった曜日に収集する。粗大ごみ通常収集とクリーンランドへの臨時持込みは別手続き。ふれあい収集ページには室内からの大型ごみ搬出の記載を確認できず、独立した搬出支援制度は今回の公式検索範囲で未発見。

- ふれあい収集（高齢者・障害者支援）（daily_support）：official_listing。資格・費用・窓口等をnew-city.jsonに記載。
- 独立した屋内搬出支援（公式検索範囲で未発見）（bulky_carry_support）：searched_not_found。資格・費用・窓口等をnew-city.jsonに記載。
- 粗大ごみ・リユース（戸別収集）（regular_bulky）：official_listing。資格・費用・窓口等をnew-city.jsonに記載。
- 臨時家庭ごみのクリーンランド持込み（self_dropoff）：official_listing。資格・費用・窓口等をnew-city.jsonに記載。

## 調査範囲・記録

- 対象は豊中市のみ。全国・近隣自治体の候補探索はしていない。
- 市公式ドメインを中心に、以下の3検索語でごみ出し支援、粗大ごみ収集、持込みを確認した。
  - `site:city.toyonaka.osaka.jp ごみ出し支援 ふれあい収集 高齢者`\n  - `site:city.toyonaka.osaka.jp 粗大ごみ 収集 申込み 手数料 豊中市`\n  - `site:city.toyonaka.osaka.jp 臨時家庭ごみ 持ち込み 予約 手数料`\n- 保存した公式ページは5件。原典のHTML/PDFと抽出テキストを `official/` に保存。
- URL、取得日時、HTTP状態、原典に表示された更新日（表示なしはnull）、原本・テキストのSHA-256は `official-metadata.json`。
- 支援条件はAND/ORを分け、親族・同居家族の援助、屋内搬出、本人搬入と運転者の別、地域差、申込・回数、減免を項目ごとに記録した。情報の未記載、検索で未発見、制度として明示された条件を区別している。
- 窓口照会と全項目の人手原文確認は未実施。保存原典に基づく独立AIレビューと指摘箇所の修正記録は `../review-osaka/` および `corrections.json` を参照。個別プレビューは未作成。

## 参照

- [new-city.json](new-city.json)
- [official-metadata.json](official-metadata.json)
- [review-locators.json](review-locators.json)
- [consumption.json](consumption.json)
