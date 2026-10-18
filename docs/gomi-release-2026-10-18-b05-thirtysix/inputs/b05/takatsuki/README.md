# 高槻市 ごみ支援調査（2026-10-18）

## 判定

高齢者等ごみ出し支援は世帯全員が対象要件を満たす場合に週1回収集し、利用料は無料。職員は室内から運び出さない。粗大な大型品や大量の片付けごみは臨時ごみの別制度で、申込み・立会い・費用が異なる。自己搬入も前日正午までの届出と重量料金が必要。

- 高齢者等ごみ出し支援（daily_support）：official_listing。資格・費用・窓口等をnew-city.jsonに記載。
- 独立した屋内搬出支援（今回の公式確認で未発見）（bulky_carry_support）：searched_not_found。資格・費用・窓口等をnew-city.jsonに記載。
- 臨時ごみ収集（大量の引越し・片付けごみ）（regular_bulky）：official_listing。資格・費用・窓口等をnew-city.jsonに記載。
- エネルギーセンターへのごみ持込み（self_dropoff）：official_listing。資格・費用・窓口等をnew-city.jsonに記載。

## 調査範囲・記録

- 対象は高槻市のみ。全国・近隣自治体の候補探索はしていない。
- 市公式ドメインを中心に、以下の4検索語でごみ出し支援、粗大ごみ収集、持込みを確認した。
  - `site:city.takatsuki.osaka.jp 高齢者等 ごみ出し支援 収集`\n  - `site:city.takatsuki.osaka.jp 粗大ごみ 臨時ごみ 収集 高槻市`\n  - `site:city.takatsuki.osaka.jp エネルギーセンター ごみ持ち込み 手数料 予約`\n  - `site:city.takatsuki.osaka.jp ごみ 屋内 搬出 支援 高齢者`\n- 保存した公式ページは5件。原典のHTML/PDFと抽出テキストを `official/` に保存。
- URL、取得日時、HTTP状態、原典に表示された更新日（表示なしはnull）、原本・テキストのSHA-256は `official-metadata.json`。
- 支援条件はAND/ORを分け、親族・同居家族の援助、屋内搬出、本人搬入と運転者の別、地域差、申込・回数、減免を項目ごとに記録した。情報の未記載、検索で未発見、制度として明示された条件を区別している。
- 窓口照会と全項目の人手原文確認は未実施。保存原典に基づく独立AIレビューと指摘箇所の修正記録は `../review-osaka/` および `corrections.json` を参照。個別プレビューは未作成。

## 参照

- [new-city.json](new-city.json)
- [official-metadata.json](official-metadata.json)
- [review-locators.json](review-locators.json)
- [consumption.json](consumption.json)
