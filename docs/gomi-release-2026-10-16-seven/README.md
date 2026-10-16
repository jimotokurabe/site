# ごみ出し支援15地域版の公開承認（2026-10-16）

運営者が最新8846プレビューと公開提案を確認後、「公開して」と明示承認。既存8地域に世田谷・札幌・名古屋・加古川・福岡・仙台・猪名川の7地域を追加する。松本は保留。元の公開提案は承認前の履歴として保持する。

候補SHA-256 `3b4d0e0ce20a5deecd7563275a214757b4141fed4be30448fca8cc16a1a19d12`、公開前main `988173439fde62f4a8d948e42f70232ef551b2a7`。承認は owner-approval.json、入力版・レビューのSHAと未確認事項は plan.json、累積レビューの原記録は inputs/ に固定保存。制度・出典・確認日は候補を保持し、公開フラグと追加7地域のレビュー受入れだけを変更した。既存8地域のcity/source object、交通本文とリンク、共通ごみCSS/JSは保持。

レビューは版固定の累積AIレビューと限定差分確認。最終版600項目の同日独立再読・人手原文全件確認ではない。人手確認状態を変更しない。世田谷冊子の現行適用、福岡日常支援の現行継続、猪名川の将来改訂日などは未確認表示と相談質問を保持する。

## 再現

`python3 docs/gomi-release-2026-10-16-seven/reproduce.py` で固定入力・承認・公開前データから外部一時フォルダへ正式データを再現し、data/gomi-support.json とのバイト一致を検査する。prepare_release.py は承認時の原ファイル。inputs 内の相対参照は当時の調査配置を表し、独立レビュー原文の追加依存資料は元の調査フォルダで保管する。

`python3 tools/validate_gomi.py --publication`、`python3 tools/build.py`、`python3 tools/check_gomi.py . --publication`、`python3 -m unittest discover -s tools -p 'test_gomi*.py'` で生成・検査する。検証結果は verification.json に保存する。

## 最新mainとの保持調整

公開直前に別セッションの計測PR #242がmain `575c762c494f2de2e0d5d8ae645628308f3bcedb` へ統合されたため、そのmainへ載せ直した。承認対象候補・制度内容・レビュー入力は不変。初回全国生成・検査は verification-before-analytics-merge.json、最新mainに対する保持再検査は verification.json に分離。新7ページだけを既存のごみ生成処理で再出力し、最新共通計測を継承。既存8ページ・交通1,741ページ・共通資産・掲載欄外のトップは最新mainと一致する。全国生成の追加実行はしない。
