# ごみ支援データの収集・検証手順

## 検証器

`tools/validate_gomi.py` はPython標準ライブラリだけで動きます。

```sh
python3 tools/validate_gomi.py
python3 tools/validate_gomi.py --data path/to/gomi-support.json
python3 tools/validate_gomi.py --publication
(cd tools && python3 -m unittest test_gomi_data.py)
```

Pythonからは `validate(data, root=None, publication=False) -> list[str]` を利用できます。`root` は `data/*-menkyo-henno.json` と自治体レコードを含むプロジェクトディレクトリです。通常検証は調査中の草稿を受け入れ、元の地域別自治体マスター、経路種別、証拠状態、根拠参照、必須項目、ISO日付、明示値と未確認値の矛盾を確認します。自治体マスターが見つからない場合もエラーです。出典URLは形式とホスト名を検査し、`.lg.jp` / `.go.jp` または `www.nishi.or.jp` / `nishi.or.jp` の政府系ホストだけを許可します。これはホストの許可リスト検査であり、そのURLの内容や個々の記述を人が確認済みである証明にはなりません。空でない値として `False` と `0` を認めるため、明示的な対象外や無料を空欄扱いしません。`not_stated` / `not_found` は値を `null` にするか、不明点の説明文だけを残します。真偽値や数値を置いて未確認を対象外・無料などに見せることはできません。`needs_confirmation` も有効な状態として保持できます。

`--publication` は公開候補の別ゲートです。`draft=false`、`not_for_publication=false`、各市の `publication_status=approved` に加え、`publication_approval` に運営者の公開承認日と対象市IDを要求します。対象外の市は公開できません。各経路には `human_reviewed` と `human_reviewed_at`、または `ai_reviewed` と `ai_reviewed_at` が必要です。AIレビューのみの場合は、そのパイロットの公開を運営者が承認した記録も必要です。検証器は承認状態や日付を自動記入しません。

2026年10月12日、試作確認後のユーザーの「公開して」に基づき4市を公開対象にしました。160項目の独立AI原文照合は完了していますが、人手原文検品を完了した記録ではありません。`human_reviewed=false`、`human_reviewed_at=null` を維持しています。この承認は全国の追加調査・追加公開には適用しません。

## 小分けの収集運用

当面は選定済み4市の検品を完了し、次の候補も**3〜5市のバッチ**で扱います。全国一括収集は行いません。既存の地域選択・全国マスターがあることを、各自治体の制度情報を調べた証拠として扱わないでください。

各バッチでは、自治体ごとに独立したデータファイルと担当者を割り当てます。同じ市のファイルを並行編集しないでください。共有の情報源台帳や共通スキーマを変更する担当は、自治体データ担当と分けます。

1. **探索:** 公式自治体ページ、添付資料、関連FAQを探し、URL・ページ見出し・確認日・更新日を記録します。取得障害は「制度なし」や「終了」に変換しません。
2. **抽出:** 4経路を分け、必須10項目を原文箇所へ結びます。明示された値、明示的な対象外、記載なし、未発見、矛盾を別状態に保ちます。不明点は `null` と質問事項にします。
3. **独立レビュー:** 抽出担当とは別の担当が公式原文と重要項目を照合し、AIか人かを記録します。AI同士の一致は人の確認の代わりになりません。対象資格のAND/OR、否定、費用と追加費用、搬出位置、点数、窓口を重点確認します。
4. **人の承認:** 実際に確認した担当者だけが、その担当種別のレビュー状態と日付を記入します。公開可否は運営者が決め、対象自治体と承認日を別に記録します。人手確認をしていないデータを人手確認済みに変更しません。通常検証と公開ゲートを両方通してから、別途ビルド・公開レビューへ渡します。
5. **統合:** バッチ担当者が自治体ファイルを統合し、重複・マスター照合・根拠リンクを再確認します。ビルドや公開はこの手順書だけでは承認されません。

既に取得済みで内容が変わっていない公式資料はキャッシュした本文・ハッシュ・取得日を再利用し、再収集対象を変更資料と未解決項目に絞ります。探索や抽出で一時エラーが出たら、同じ処理の再試行は1回まで。その後は失敗理由と対象URLを記録し、人の確認または別の公式資料へ切り替えます。無限再試行をしません。

## バッチ記録ひな型

所要時間やトークンは計測できた場合だけ記録し、推定値を実績に混ぜません。費用は運営者が確認した公式モデル料金方針に従い、未確認の単価や「クレジット価格」を作りません。

```json
{
  "batch_id": "2026-10-batch-01",
  "city_ids": ["hyogo:kobe", "hyogo:nishinomiya"],
  "owner": null,
  "status": "planned",
  "model": null,
  "effort": null,
  "research_minutes": null,
  "extraction_minutes": null,
  "independent_review_minutes": null,
  "waiting_minutes": null,
  "tokens_input": null,
  "tokens_output": null,
  "token_measurement_source": null,
  "errors": [],
  "reviewed_by": null,
  "reviewed_at": null,
  "publication_decision": "pending"
}
```

`status` は `planned` → `exploring` → `extracted` → `independent_review` → `human_approved` → `merged` の実際の進捗だけを記録します。`model` と `effort` は実際に使った値、所要時間・トークンは観測値を記入します。何も測っていなければ `null` のままです。


## 今回の実装と確認方法

現在は `data/gomi-support.json` の4市を1ファイルで管理しています。自治体別ファイルを自動統合するジョブ実行器・全国自動収集・差分監視は未実装です。上記の小分け運用は今後の担当手順です。次のバッチでは作業ファイルを自治体ごとに分け、統合担当が検査済みデータだけこのファイルへ取り込みます。

公開前の確認は、リポジトリ直下以外の出力先を指定します。

```sh
python3 tools/build.py --draft --gomi-preview --out ../調査/2026-10-12_ごみ出し支援実装/preview
python3 tools/check_gomi.py ../調査/2026-10-12_ごみ出し支援実装/preview
python3 -m unittest discover -s tools -p 'test_*.py'
```

`--gomi-preview` には `--draft` と別の `--out` が必要です。通常ビルドでは草稿のごみデータを読み込まず、トップも既存のままです。公開候補に切り替える場合はデータの `draft` だけを変更しても通りません。レビュー記録と対象範囲を含む公開ゲート全項目を満たす必要があります。下書き出力先の再利用による混入を防ぐため、草稿ごみHTMLが残る出力先での通常ビルドは拒否します。

画面はテーマ入口＋データにある各市のページを生成します。`pref:slug` から既存地域との対応とURLを作り、件数・地域名を画面内に固定していません。未調査地域のページは作りません。`tools/gomi_integration.py` がトップの説明と入口、および対象市の交通支援ページからの関連リンクを生成後に追加します。

メモの入力内容は画面内だけで扱います。文字サイズの設定だけは既存ページと同じ `sessionStorage` の `jk-national-size` を共用し、メモや介護・世帯情報を保存しません。コピーしたメモには条件・料金・相談先・公式URL・確認日・未解決の質問を残します。追記で元の質問は消えません。「相談メモを印刷」は選択した経路のメモを印刷し、ブラウザーの通常印刷は本文も含みます。

公的URLの許可リストにない独自ドメインを追加する際は、自治体の公式案内から当該ドメインへのリンク等を確認し、根拠とともに検証器の許可リストを更新します。抽出担当が検査を通すためだけに任意の業者ドメインを追加することはしません。

公開候補の確認：

```sh
python3 tools/build.py
python3 tools/validate_gomi.py --publication
python3 tools/check_gomi.py . --publication
python3 tools/check_publication.py
python3 tools/check_national_records.py
```
