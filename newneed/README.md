# newneed（ニーズ領域表示・看護計画モジュール）

アセスメント票のデータをもとに、**23項目（N01～N23）のニーズ領域**のうち「該当した項目」だけを抽出して一覧表示し、**看護計画書**の入力・保存・PDF出力まで行うモジュールです。

---

## 目次

- [このモジュールでできること](#このモジュールでできること)
- [ディレクトリ構成](#ディレクトリ構成)
- [画面の使い方](#画面の使い方)
- [API一覧](#api一覧)
- [設定ファイル（管理者・開発者向け）](#設定ファイル管理者開発者向け)
- [よくあるトラブル](#よくあるトラブル)
- [関連ドキュメント](#関連ドキュメント)

---

## このモジュールでできること

| 機能 | 説明 |
|------|------|
| **ニーズ領域の抽出表示** | 事業所番号・個人番号・評価回次を指定すると、アセスメントデータから「値が立った」ニーズ領域（N01～N23）だけを一覧表示する |
| **看護計画の記入・保存** | 各ニーズ領域ごとに看護目標・ケア内容・支援方法・前回からの変化などを入力し、DBに保存する |
| **看護計画のPDF出力** | 看護計画画面からブラウザの印刷機能でPDFに保存できる |

**23項目（ニーズ領域）の例:** 収入／家計、福祉用具／住宅改修、介護者の負担、栄養／食事、口腔ケア、衛生、排泄、リハビリ、移動、ADL、精神心理、薬物療法 など（詳細は `spec/needs_master_schema.csv` 参照）。

---

## ディレクトリ構成

```
newneed/
├── README.md                    # このファイル
├── 操作手順書.md                 # 詳細な操作手順（画面・API・設定変更）
├── api_router.py                # FastAPI ルーター（API・表示ロジック）
├── column_display_text.csv      # カラムごとの表示文言（画面上の「該当内容」のテキスト）
├── sync_display_text_to_schema.py  # 表示文言を need_rules_schema に同期するスクリプト
├── spec/
│   ├── needs_master_schema.csv   # ニーズマスター（N01～N23 の名称など）
│   └── need_rules_schema.csv     # ニーズ判定ルール（どのカラムがどのニーズに紐づくか）
└── static/
    ├── display.html              # ニーズ領域表示画面
    ├── care-plan.html            # 看護計画画面
    └── display.css               # 共通スタイル
```

- **利用者・運用者** … `static/` の画面（`display.html` / `care-plan.html`）を使います。
- **管理者・開発者** … `spec/` のCSVや `column_display_text.csv` を編集して表示内容を変更できます。

---

## 画面の使い方

### 前提

- バックエンド（FastAPI）が起動していること
- ブラウザで次のURLにアクセスできること

### アクセスURL（例: ローカル）

| 用途 | URL |
|------|-----|
| **ニーズ領域表示画面（メイン）** | `http://localhost:8000/api/newneed/page` または `http://localhost:8000/api/newneed/static/display.html` |
| **看護計画画面** | ニーズ領域表示画面で「看護計画を書く」をクリックすると遷移（URLに `care-plan.html` が含まれる） |

### ニーズ領域を表示する手順

1. 上記URLで **ニーズ領域抽出システム** の画面を開く
2. **事業所番号**（例: `A001`）・**個人番号**（例: `0001`）・**回次**（1回目／2回目／3回目）を入力
3. **「表示」** をクリック
4. 該当データがあれば、**該当したニーズ領域だけ**が一覧表示される
5. 各ブロックの **「看護計画を書く」** で、そのニーズ用の看護計画画面へ移動

### 看護計画を書く手順

1. ニーズ領域表示画面で、対象ニーズの **「看護計画を書く」** をクリック
2. 左側の **該当内容** を参照しながら、右側のフォームに看護目標・ケア内容・支援方法・前回からの変化などを入力
3. **「保存」** で保存
4. **「PDF」** で印刷ダイアログを開き、「PDFに保存」でPDF出力可能
5. **「← ニーズ領域一覧に戻る」** で表示画面に戻る

---

## API一覧

他システムやフロントから連携するときの代表的なAPIです。

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/newneed/` | モジュール状態確認（`{"module":"newneed","status":"ok"}`） |
| GET | `/api/newneed/display` | 23項目表示用JSON取得（クエリ: `user_id` または `office_id`+`personal_id`、`round`） |
| GET | `/api/newneed/page` | 表示画面（display.html）へリダイレクト |
| GET | `/api/newneed/care-plan/form` | 看護計画フォーム用データ取得（`user_id`, `round`, `need_id` など） |
| POST | `/api/newneed/care-plan` | 看護計画の保存（JSON body） |

**表示データ取得の例（GET `/api/newneed/display`）**

- クエリ: `user_id=A001_0001` または `office_id=A001` & `personal_id=0001`、任意で `round=1`（省略時は1）
- レスポンス: `user_id`, `assessment_round`, `items`（各要素に `need_id`, `need_name_jp`, `contents`）

詳細なパラメータ・レスポンス例は **操作手順書.md** の「5. API」を参照してください。

---

## 設定ファイル（管理者・開発者向け）

表示内容は以下のCSVで制御されています。

| ファイル | 役割 |
|----------|------|
| **spec/needs_master_schema.csv** | N01～N23 の名称（`need_name_jp` など）を定義 |
| **spec/need_rules_schema.csv** | どのアセスメント項目（カラム）がどのニーズに紐づくか、条件（`if_column`, `operator`, `target_value`）を定義 |
| **column_display_text.csv** | 画面上の「該当内容」に表示する文言（`need_id`, `column_name`, `display_text`） |

- **表示文言を変えたい** → `column_display_text.csv` の `display_text` を編集
- **ニーズ名を変えたい** → `spec/needs_master_schema.csv` の `need_name_jp` を編集
- **どの項目をどのニーズに含めるか変えたい** → `spec/need_rules_schema.csv` を編集（変更後はAPIサーバーを再起動すると反映されます）

### 表示文言をスキーマに反映する

`column_display_text.csv` の内容を `spec/need_rules_schema.csv` の `confidence_note` に反映したいときに使うスクリプトです。

```bash
# プロジェクトルート（backend または app の親）で実行
python -m app.newneed.sync_display_text_to_schema
```

---

## よくあるトラブル

| 現象 | 確認すること |
|------|----------------|
| 画面が表示されない | バックエンドが起動しているか、URLが `/api/newneed/page` または `/api/newneed/static/display.html` か確認 |
| 「レコードが見つかりません」 | 指定した事業所番号・個人番号・回次のデータがDBまたはCSVに存在するか確認 |
| 該当項目が一つも表示されない | アセスメントデータの該当カラムに値が入っているか、`need_rules_schema.csv` のルールが正しいか確認 |
| 表示文言が想定と違う | `column_display_text.csv` の `display_text` を確認・修正。必要なら `sync_display_text_to_schema.py` を実行 |
| 看護計画が保存されない | ネットワーク・サーバーエラーの有無、POST先が `/api/newneed/care-plan` であること、必須項目（`user_id`, `assessment_round`, `need_id`）が送られているかを確認 |

---

## 関連ドキュメント

- **操作手順書.md** … 画面操作の詳細、APIパラメータ・レスポンス例、設定ファイルの編集方法、トラブルシューティングを記載しています。

---

*このモジュールは FastAPI アプリに `/api/newneed` プレフィックスでマウントされています（`main.py` で `newneed_router` を include）。*
