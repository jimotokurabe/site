# さいたま市 ごみ支援調査（2026-10-18・公開前草稿）

## 結論と候補選定

さいたま市を埼玉県の初候補として調査した。市公式ページで、ふれあい収集、粗大ごみ戸別収集、処理施設への直接持込みと予約を確認でき、通常の粗大ごみ収集・処理料金も別経路で整理できる。単身と同居世帯の条件を分けて記録でき、本人持込みの解釈や屋内搬出の制約も公式文言に沿って示せるため、4経路の候補として資料充足度は高い。

屋内搬出支援制度は公式検索・確認資料内で未発見。これは制度が存在しないという確認ではない。通常の粗大ごみ戸別収集は屋内（集合住宅は建物内）から収集しないと明記されている。処理手数料と屋内搬出作業料・免除を混同せず、後者は要照会とした。

## 4経路の記録

- 日常支援：ふれあい収集。単身の高齢者、同居家族がいる高齢者、単身障害者、同居家族がいる障害者を原文の枝ごとに構造化した。同居の場合は同居者も高齢者・障害者等で、収集所まで運べない事情が必要。職員の訪問調査後に収集方法を調整する。
- 粗大ごみ搬出支援：独立した屋内搬出支援制度は調査範囲内で未発見。通常の戸別収集は屋内搬出なし。料金・対象資格が未確認のため、制度なしや無料とは記載していない。
- 通常の粗大ごみ：戸別収集。90cm以上2m未満の粗大ごみ、品目別の処理手数料、屋外の指定場所、1回4品、予約・納付券、立会い不要を別記。
- 自己搬入：市内発生の家庭ごみを本人が自動車で持込み、完全事前予約制。本人が運転する条件とは読み替えず、家族の運転・同乗・積込み補助を質問に残した。持込処理料金と戸別収集料金を分けた。

2026年の重量制料金は、計量表示10kg以下無料、10kgを超えると最初の10kgから180円/10kg（税抜、消費税相当額を加算、10円未満切捨て）。適用期間と品目別料金の区別を保持。2027年改定予定の金額は現行料金に混ぜていない。

## 調査・保存

さいたま市公式ドメイン限定の検索を6クエリ行い、公式資料8件をHTTP 200で取得した。検索実行時刻は記録されていないのでnull。原典取得時刻、取得日、URL、HTTP状態、Content-Type、取得時に確認できた公式更新日、原典SHA-256は `sources/*metadata.json` に保存。HTTP応答は `.html.source` / `.pdf.source`、読みやすい抽出本文は `.txt`。PDF等で原典上の日単位の更新日が取れない場合はnull。

`review-locators.json` はサービス・項目から原典テキスト行番号、引用行、原典ファイルとSHA-256へ対応付ける。ページ本文の行番号は保存した抽出テキストの1始まり。原典応答自体は対応するrawファイルとhashで固定している。検索語と未発見判定の範囲は `official-search-log.json`。

## 状態とプレビュー

`new-city.json` は `ai_draft: true`, `human_reviewed: false`, `draft: true`, `not_for_publication: true`。全4サービスを `ai_draft` とし、別担当レビュー・人手原文全項目確認・窓口確認は未実施。公開採用判断は保留。validatorのスキーマ通過は制度内容の正確性を証明しない。

`preview/` には全国入口、埼玉県入口、さいたま市詳細の3ページがある。リンクエラー0、交通ページ再生成0、草稿表示を確認した。これは料金の「無料枠超過後は最初の10kgから課金」の明記前に生成された個別プレビューであり、現在の修正版HTMLではない。検査用統合プレビューは親側で作成する。

- `preview/gomi-support.html`
- `preview/saitama-gomi-support/index.html`
- `preview/saitama-gomi-support/saitama.html`

検証結果 `validation.json` はVALID。preview builderは対象repoから読み取り、出力をこのpreviewフォルダ内に限定した。再生成：

```sh
python3 -c "import json,sys; from pathlib import Path; sys.path.insert(0,'gomi-expansion-b03/tools'); from validate_gomi import validate; d=json.loads(Path('調査/2026-10-18_ごみ支援拡大B03/saitama/new-city.json').read_text()); e=validate(d,root=Path('gomi-expansion-b03')); print('\\n'.join(e) if e else 'VALID'); sys.exit(bool(e))"
python3 gomi-expansion-b03/tools/build_gomi_preview.py --data 調査/2026-10-18_ごみ支援拡大B03/saitama/new-city.json --out 調査/2026-10-18_ごみ支援拡大B03/saitama/preview --base gomi-release-preview
```

## 取り込み時の注意

親側で候補を集約する場合も、このファイルの `new-city.json` を草稿状態のまま独立レビューへ渡す。レビューで指摘された条件の修正後に限り、レビュー結果と差分を記録する。既存公開データへ直接取り込まず、公開承認や `ai_reviewed` 状態を付与しない。処理料金、搬出支援料金、減免の根拠を分離し、単身/同居条件、本人搬入/本人運転を混同しない。

## 最終ファイルhash

- `new-city.json`: `121624595883899185fd9bad5d8a709673ca85510c26f5946be1e036f1c61f6d`
- `review-locators.json`: `cec5cf44fb3e03cbfd04c82862f1fb08dfb7050d53d84af32349c762ca975b76`
- `official-search-log.json`: `4c5853fa720355b6cce1de82951b891107f4136283b68bc85eb81f02420756f2`
- `preview/generation-manifest.json`: `41de2ee57e94131e6a7cff27e7913218c72438d285ca823e3106930ccd2148be`

SHA-256は2026-10-18の最終ファイルから算出。これ以降は内容を変更しない。
