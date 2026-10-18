# 川西・姫路追加、19地域版の公開承認（2026-10-18）

運営者の「川西・姫路の2市を公開して」を受け、承認候補・独立AI照合・公式保存原典・画面検証・台帳をinputsへ固定。owner-approval.jsonに承認範囲、plan.jsonに入力hashを保存。原典HTMLは内容を変えず.html.sourceとし、公開ページ検査から分離。

新規2市80項目と既存17地域680項目で計760項目。既存17city/104source、17ごみHTML、1741交通HTML、全共通資産を保持。人手原文全件確認・窓口確認・利用者効果実証ではない。

`python3 docs/gomi-release-2026-10-18-b01-nineteen/reproduce.py`で承認済み正式データをバイト再現（--writeで書出し）。`PYTHONHASHSEED=0 python3 docs/gomi-release-2026-10-18-b01-nineteen/build_release.py`でごみ20頁だけ生成・照合。トップ掲載地域欄、sitemap新2URLのみ更新。`verify_release.py`で基準mainと保持・出典日付・質問を照合。

原典取得14、再利用3。実装Sol medium1名、独立Luna medium1名・80項目1回、必要訂正0。親モデル不変。credits不明。公開前検証はverification.json、実公開照合はpublication-record.jsonを参照。
