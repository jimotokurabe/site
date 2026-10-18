# 宝塚・伊丹追加、17地域版の公開承認（2026-10-18）

運営者は8847の宝塚プレビューと今回2市を追加する17地域公開提案の確認後、「公開して」と明示承認。実承認は owner-approval.json。候補SHA-256は `276262c0fda573c870c474c4564d4e62310a1bb8a2a03aef5dc991ab333518f9`。既存15地域と95出典は変更せず、2市80項目を追加し17地域680項目とする。

入力版・累積AI照合台帳・公式保存資料・先行画面確認結果を inputs に固定保存。保存HTMLは公開ページ検査の対象と混同しないよう `.html.source` とし、内容は原取得のまま。plan.jsonに全入力hashを記録。追加8経路の2026-10-16独立AI確認と親3重点照合を受入れ。全680項目を同日再読した記録でも、人手原文全件確認でもない。人手確認状態・制度値・出典・確認日・質問を変更しない。伊丹の受付期限差や室内対応等の未確認事項を保持。

元gomi-release-previewに他作業の未commit差分1747ファイルがあったため、最新main 749e5bf7から独立worktree gomi-publish-seventeenを作成。元checkout・交通根拠作業・計測作業・旧8847は無変更。共有コードは当該市と正確URLに限定した公式host許可のみ。

`python3 docs/gomi-release-2026-10-18-two/reproduce.py` は承認・入力hash・以前の正式データから今回正式データをメモリ内再現しバイト照合。`--write` は明示的に正式データを書き出す。

`PYTHONHASHSEED=0 python3 docs/gomi-release-2026-10-18-two/build_release.py` は既存の公開ごみ生成APIで18ページを生成・照合。既存15地域はバイト一致を要求し、新2ページと一覧のみ書込。トップは掲載地域欄のみ、sitemapは新2URLのみ追加。全国再生成はしない。

公開ゲート、28ごみテスト、計測生成2テスト、全公開ページ検査、保持検査の結果は verification.json。`python3 docs/gomi-release-2026-10-18-two/verify_release.py` で基準mainに対する1741交通HTML・15ごみHTML・全共通資産保持と制度項目の出典/日付/質問を検査。プレビュー時のスマホ・文字拡大・経路切替・コピー・印刷DOM確認はinputs/browser-check.json。実紙印刷・利用者効果の実証ではない。
