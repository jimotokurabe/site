# 松江市 ごみ支援調査（2026-10-18）

日常は個別事情と道路条件を考慮する戸別変更。通常粗大は年4回・1回2個の上限。

## 経路

- 日常のごみ出し支援（daily_support）：official_listing
- 粗大ごみの屋内・玄関先搬出支援（bulky_carry_support）：searched_not_found
- 通常の粗大ごみ収集（regular_bulky）：official_listing
- 処理施設への自己搬入（self_dropoff）：official_listing

## 原典と状態

- 公式原典 4件を `official/` に保存。URL、実取得日時、HTTP、原本と抽出文のSHA-256は `official-metadata.json`。
- 根拠箇所は `review-locators.json`。10項目×4経路を `new-city.json` に記録。
- 独立原典レビュー、人手確認、自治体窓口照会、プレビュー作成は未実施。AI下書き・公開不可。
- 検索・取得・消費と候補SHA-256は `consumption.json`。
