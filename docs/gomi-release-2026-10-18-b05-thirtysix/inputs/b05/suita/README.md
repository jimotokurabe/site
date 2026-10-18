# 吹田市 ごみ支援調査（2026-10-18）

## 判定

安心サポート収集は要介護・障がい等の本人と同居者が排出困難で、親族や近隣の援助がない場合に利用できる。大型複雑ごみは安全に玄関口から運べるものに限る個別協議。通常収集日は地区ごとに異なり、臨時持込みも前日予約・本人搬入・有料の条件がある。

- 吹田市安心サポート収集（daily_support）：official_listing。資格・費用・窓口等をnew-city.jsonに記載。
- 安心サポート収集（大型複雑ごみの個別搬出）（bulky_carry_support）：official_listing。資格・費用・窓口等をnew-city.jsonに記載。
- 大型複雑ごみ（定期収集）（regular_bulky）：official_listing。資格・費用・窓口等をnew-city.jsonに記載。
- 破砕選別工場へのごみ持込み（self_dropoff）：official_listing。資格・費用・窓口等をnew-city.jsonに記載。

## 調査範囲・記録

- 対象は吹田市のみ。全国・近隣自治体の候補探索はしていない。
- 市公式ドメインを中心に、以下の4検索語でごみ出し支援、粗大ごみ収集、持込みを確認した。
  - `site:city.suita.osaka.jp 安心サポート収集 対象 申込み`\n  - `site:city.suita.osaka.jp 粗大ごみ 大型複雑ごみ 収集 出し方`\n  - `site:city.suita.osaka.jp 破砕選別工場 持込み 予約 手数料`\n  - `site:city.suita.osaka.jp ごみ収集日 大型複雑ごみ 地区`\n- 保存した公式ページは5件。原典のHTML/PDFと抽出テキストを `official/` に保存。
- URL、取得日時、HTTP状態、原典に表示された更新日（表示なしはnull）、原本・テキストのSHA-256は `official-metadata.json`。
- 支援条件はAND/ORを分け、親族・同居家族の援助、屋内搬出、本人搬入と運転者の別、地域差、申込・回数、減免を項目ごとに記録した。情報の未記載、検索で未発見、制度として明示された条件を区別している。
- 窓口照会と全項目の人手原文確認は未実施。保存原典に基づく独立AIレビューと指摘箇所の修正記録は `../review-osaka/` および `corrections.json` を参照。個別プレビューは未作成。

## 参照

- [new-city.json](new-city.json)
- [official-metadata.json](official-metadata.json)
- [review-locators.json](review-locators.json)
- [consumption.json](consumption.json)
