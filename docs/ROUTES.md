# Web アプリ ルート一覧

以下は、検出した主要ルートの一覧（URL、HTTP メソッド、担当ファイル、短い説明、権限）です。

---

## トップ / ダッシュボード

- **GET /**  
  - ファイル: `app/__init__.py`（index）  
  - 説明: 認証済みユーザ向けホームダッシュボード。候補者・応募・面接・評価のサマリと直近30日分のグラフを表示。未認証は `/auth/login` にリダイレクト。  
  - 権限: 要ログイン

- **GET /dashboard-2**  
  - ファイル: `app/__init__.py`（dashboard_2）  
  - 説明: 詳細な分析ダッシュボード（フィルタ、チャート、応募→内定のYield等）。  
  - 権限: 要ログイン

## 認証（`/auth`）

- **GET, POST /auth/login**  
  - ファイル: `app/blueprints/auth/routes.py`  
  - 説明: ログインフォーム表示と認証処理。成功時はダッシュボードへリダイレクト。

- **POST /auth/logout**  
  - ファイル: `app/blueprints/auth/routes.py`  
  - 説明: ログアウト処理（POST）。

- **GET, POST /auth/signup**  
  - ファイル: `app/blueprints/auth/routes.py`  
  - 説明: 初回および管理者によるユーザ作成。最初のユーザ作成は制限なし、以降は admin のみ。

- **GET /auth/users**  
  - ファイル: `app/blueprints/auth/routes.py`  
  - 説明: 管理者向けユーザ一覧ページ（`@admin_required`）。

## 候補者（`/candidates`）

- **GET /candidates**  
  - ファイル: `app/blueprints/candidates/routes.py`  
  - 説明: 候補者一覧（検索・フィルタ・ページネーション）。

- **GET, POST /candidates/create**  
  - ファイル: `app/blueprints/candidates/routes.py`  
  - 説明: 候補者作成フォームと保存。

- **GET, POST /candidates/<int:candidate_id>**  
  - ファイル: `app/blueprints/candidates/routes.py`  
  - 説明: 候補者詳細（プロフィール編集、ステージ更新、面接/評価一覧表示、ファイル管理等）。

- **POST /candidates/<int:candidate_id>/upload_resume**  
  - ファイル: `app/blueprints/candidates/routes.py`  
  - 説明: 履歴書ファイルをアップロードして `Files` を作成。ストレージ保存。

- **GET /candidates/<int:candidate_id>/files**  
  - ファイル: `app/blueprints/candidates/routes.py`  
  - 説明: 候補者に紐づくファイル一覧表示。

- **GET /candidates/<int:candidate_id>/files/<int:file_id>/download**  
  - ファイル: `app/blueprints/candidates/routes.py`  
  - 説明: ファイルをダウンロード（stream）。

- **GET /candidates/<int:candidate_id>/files/<int:file_id>/view**  
  - ファイル: `app/blueprints/candidates/routes.py`  
  - 説明: 可能ならプレビュー（office→HTML 等）、無ければ生データを返す。

- **GET /candidates/<int:candidate_id>/evaluation**  
  - ファイル: `app/blueprints/candidates/routes.py`  
  - 説明: 候補者の最新総合評価を再計算して保存・表示（必要に応じ再計算パラメータあり）。

## 面接（`/interviews`）

- **GET /interviews**  
  - ファイル: `app/blueprints/interviews/routes.py`  
  - 説明: 面接一覧（「今日」のカード、フィルタ、ページネーション）。クライアントの tz を受け取りユーザ設定へ保存可能。

- **GET, POST /interviews/create**  
  - ファイル: `app/blueprints/interviews/routes.py`  
  - 説明: 面接作成フォーム。録音ファイルがアップロードされた場合は `Recording` 作成、解析ページへリダイレクト。

- **GET, POST /interviews/<int:interview_id>**  
  - ファイル: `app/blueprints/interviews/routes.py`  
  - 説明: 面接詳細・編集。最新の `Transcript.text` を読み込み `interview.transcript_text` に付与して表示。評価一覧や処理ステータス（processing/ok/error）の表示あり。

- **GET /interviews/<int:interview_id>/ics**  
  - ファイル: `app/blueprints/interviews/routes.py`  
  - 説明: 予定を ICS ファイルでダウンロード。

- **POST /interviews/<int:interview_id>/upload**  
  - ファイル: `app/blueprints/interviews/routes.py`  
  - 説明: 録音ファイルアップロード。`Recording` 作成後に RQ へ `transcribe_recording` を enqueue（非同期文字起こし開始）。

- **GET /interviews/<int:interview_id>/analyze**  
  - ファイル: `app/blueprints/interviews/routes.py`  
  - 説明: 指定 (または最新) 録音について transcribe ジョブをキックして UI に通知（enqueue）。

## 管理（`/org`）

- **GET /org/settings**  
  - ファイル: `app/blueprints/org/routes.py`  
  - 説明: 組織設定ダッシュボード。

- **GET, POST /org/heuristic**  
  - ファイル: `app/blueprints/org/routes.py`  
  - 説明: 音声処理ヒューリスティックの編集（DG_WORD_GAP_THRESHOLD、FILLER_TOKENS 等）。`@admin_required`。

- **GET, POST /org/export**  
  - ファイル: `app/blueprints/org/routes.py`  
  - 説明: 選択テーブルを JSON としてエクスポート（admin）。

- **GET, POST /org/import**  
  - ファイル: `app/blueprints/org/routes.py`  
  - 説明: CSV / JSON インポート用（候補者等のバルク登録、admin）。

- **GET /org/import/template**  
  - ファイル: `app/blueprints/org/routes.py`  
  - 説明: CSVインポート用テンプレートダウンロード。

- **GET, POST /org/users**  
  - ファイル: `app/blueprints/org/routes.py`  
  - 説明: 組織ユーザ管理（タイムゾーン設定等、admin）。

## ジョブ API（`/jobs`）

- **POST /jobs/evaluate**  
  - ファイル: `app/blueprints/jobs/forms.py`  
  - 説明: `application_id` を受け取り評価ジョブ（RQ）を enqueue。要ログイン。

- **POST /jobs/notify**  
  - ファイル: `app/blueprints/jobs/forms.py`  
  - 説明: 通知ジョブ（メール等）を enqueue（パラメータ: application_id, to, subject, html）。要ログイン。

## アプリ内 API（追加）

- **POST /api/interviews/<int:interview_id>/audio/deepgram**  
  - ファイル: `app/api/dg_transcribe.py`  
  - 説明: 音声ファイルアップロード → 一時保存 → `transcribe_whisper` を呼んで簡易プレビューを返す（Deepgram 名義のエンドポイントだが内部で whisper を使用する実装）。戻り: transcript preview。  
  - 注意: ローカルアップロードディレクトリ `instance/uploads` を使用。

- **POST /api/interviews/<int:interview_id>/analyze**  
  - ファイル: `app/api/analyze.py`  
  - 説明: Interview の transcript/segments を利用して発話メトリクスを計算し、OpenAI（Responses）等で要約・JSON評価を生成して Interview に保存する。Evaluation レコードも互換性のため生成する。戻りはスコア/要約/metrics。

## 実装上の補足（運用・権限）

- 多くの UI は「要ログイン」。管理操作は `@admin_required`（org の一部ページ）で保護されています。  
- 面接のアップロードは非同期処理（RQ）を前提としており、トランスクリプトは `transcripts` テーブルへ保存される（`status`／`utterances`／`metrics` フィールドあり）。  
- 設定（`DG_WORD_GAP_THRESHOLD` 等）は UI で編集でき、処理パイプラインが参照します。  
- `app/__init__.py` で個別に Blueprint を register しているため、1 つの blueprint の不具合がアプリ全体を壊さないようになっています。

---
