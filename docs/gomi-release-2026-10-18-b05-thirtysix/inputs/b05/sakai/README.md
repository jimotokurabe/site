# 堺市 ごみ支援調査（2026-10-18）

## 判定

堺市では、生活ごみ・資源の定期支援と、屋内から運び出す粗大ごみ支援を分けて実施。家庭ごみの通常収集と自己搬入にも別の手順・費用がある。支援には身近な人の協力が得られない等の条件があり、世帯状況・住居・品目ごとの確認が必要。

- ふれあいサポート収集（生活ごみ・資源等）（daily_support）：official_listing。資格・費用・窓口等をnew-city.jsonに記載。
- ふれあいサポート収集（粗大ごみ屋内搬出）（bulky_carry_support）：official_listing。資格・費用・窓口等をnew-city.jsonに記載。
- 粗大ごみ（通常収集）（regular_bulky）：official_listing。資格・費用・窓口等をnew-city.jsonに記載。
- クリーンセンター清掃工場への持込み（self_dropoff）：official_listing。資格・費用・窓口等をnew-city.jsonに記載。

## 調査範囲・記録

- 対象は堺市のみ。全国・近隣自治体の候補探索はしていない。
- 市公式ドメインを中心に、以下の3検索語でごみ出し支援、粗大ごみ収集、持込みを確認した。
  - `site:city.sakai.lg.jp ごみ ふれあいサポート収集 粗大ごみ 屋内`\n  - `site:city.sakai.lg.jp 粗大ごみ 申込 手数料 持込み`\n  - `site:city.sakai.lg.jp 家庭ごみ 清掃工場 持込み 予約 手数料`\n- 保存した公式ページは5件。原典のHTML/PDFと抽出テキストを `official/` に保存。
- URL、取得日時、HTTP状態、原典に表示された更新日（表示なしはnull）、原本・テキストのSHA-256は `official-metadata.json`。
- 支援条件はAND/ORを分け、親族・同居家族の援助、屋内搬出、本人搬入と運転者の別、地域差、申込・回数、減免を項目ごとに記録した。情報の未記載、検索で未発見、制度として明示された条件を区別している。
- 窓口照会と全項目の人手原文確認は未実施。保存原典に基づく独立AIレビューと指摘箇所の修正記録は `../review-osaka/` および `corrections.json` を参照。個別プレビューは未作成。

## 参照

- [new-city.json](new-city.json)
- [official-metadata.json](official-metadata.json)
- [review-locators.json](review-locators.json)
- [consumption.json](consumption.json)
