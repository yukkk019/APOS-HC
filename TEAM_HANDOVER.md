# APOS-HC 引き継ぎメモ（ローカル起動と構成）

このドキュメントは、チームメンバーがローカルで画面を開き、開発を開始するための最短手順です。

## 1. まず動かす（最短）

このリポジトリは、ローカル確認時に以下の2つを別ターミナルで起動します。

- APIサーバー（`submit_server.py`）
- フロント配信（`frontend/index.html` を静的配信）

### ターミナル1: APIサーバー起動

```powershell
cd C:\Users\yukin\Desktop\Apos-hc
pip install -r requirements.txt
uvicorn submit_server:app --reload --host 127.0.0.1 --port 8000
```

### ターミナル2: フロント配信

```powershell
cd C:\Users\yukin\Desktop\Apos-hc
python -m http.server 5500
```

### ブラウザで開くURL

- 全体トップ画面: `http://127.0.0.1:5500/frontend/index.html`
- APIドキュメント: `http://127.0.0.1:8000/docs`

## 2. 重要な注意（`{"detail":"Not Found"}` の理由）

現在の `submit_server.py` は主に以下のエンドポイントを持つローカル確認用APIです。

- `POST /save`
- `POST /submit`
- `GET /verify/latest`
- `GET /verify/user/{user_id}`
- `GET /verify/round-status/{user_id}`
- `GET /verify/consistency/{user_id}`

そのため、`/api/newneed/...` に直接アクセスすると `{"detail":"Not Found"}` になります。

`newneed` 系画面（`/api/newneed/page` など）を使うには、`newneed/api_router.py` を `include_router` した本体FastAPIアプリが別途必要です。

## 3. フォルダ構成（主要）

```text
Apos-hc/
├── frontend/                  # 入力UI（ブラウザ）
│   ├── index.html             # 全体トップ画面
│   └── js/
│       ├── main.js            # 画面制御の司令塔
│       ├── renderer.js        # フォーム描画
│       └── formDefs/page*.js  # 各ページ定義（0〜19）
├── newneed/                   # ニーズ領域表示・看護計画モジュール
│   ├── api_router.py          # newneed APIルーター
│   ├── static/                # display/care-plan のHTML/CSS
│   ├── spec/                  # ニーズ判定ルールCSV
│   └── README.md              # newneed詳細説明
├── submit_server.py           # ローカル確認用FastAPI（save/submit/verify）
├── apos_hc.db                 # SQLite DB
└── requirements.txt
```

## 4. フロントとAPIの関係

- `frontend/js/main.js` から以下へ送信します。
  - 一時保存: `http://localhost:8000/save`
  - 最終送信: `http://localhost:8000/submit`
- そのため、フロントは `5500` でも、APIは `8000` が必要です。

## 5. よくあるトラブル

### `uvicorn: command not found`

```powershell
python -m pip install uvicorn
```

### 画面は開くが保存/送信に失敗する

- `submit_server.py` が `8000` で起動しているか確認
- ブラウザの開発者ツールで `POST /save` と `POST /submit` のレスポンスを確認

### `{"detail":"Not Found"}` が出る

- `http://127.0.0.1:8000/docs` に目的APIがあるか確認
- `submit_server.py` 起動中は `/api/newneed/...` は基本的に未提供

## 6. チーム開発時の基本運用（推奨）

- `main` には直接コミットしない
- 個人ブランチで作業してPRを作る
  - 例: `feature/<name>`
- 作業の流れ:
  1. `git checkout feature/<name>`
  2. 編集
  3. `git add .`
  4. `git commit -m "..."`  
  5. `git push`
  6. GitHubで `main` 向けPR作成

---

必要なら次の担当者向けに、`newneed` を含めた「本体FastAPIの起動手順（1コマンド運用）」版も別紙で追記してください。
