# データベース設計書（概要）

この設計書は `app/models` に定義された SQLAlchemy モデルを元に、主要テーブルのカラム一覧・型・外部キー・簡単な説明をまとめたものです。実運用での詳細（インデックス、nullable、デフォルト値等）はモデルを参照してください。

---

## テーブル一覧
- users
- organizations
- candidates
- applications
- interviews
- recordings
- transcripts
- files
- interview_evaluations
- candidate_overall_evaluations
- settings
- notifications
- sources

---

## users
- id: Integer PK
- org_id: Integer (組織ID、index)
- email: String(255), unique, not null
- password_hash: String(255), not null
- role: String(50) (例: admin)
- tz_offset_minutes: Integer, nullable (クライアントの timezone offset)

用途: アプリのユーザ認証・権限管理。Flask-Login の UserMixin を使用。

---

## organizations
- id: Integer PK
- name: String(120), unique, not null

用途: マルチテナントの組織情報。

---

## candidates
- id: Integer PK
- org_id: Integer (OrgScopedMixin)
- name: String(120), not null
- name_yomi: String(160)
- email: String(254), unique?, index?
- phonenumber: String(40)
- birthdate: Date
- memo: Text
- applying_position: String(100), index
- nationality: String(100), index
- school: String(200)
- grad_year: Integer
- current_job: Text
- resume_file_id: Integer FK -> files.id (nullable)
- qualifications: JSON
- languages: JSON
- skills: JSON
- applied_at: Date (server_default now)
- status: String(30) (applied/screening/offer/hired/rejected/withdrawn)
- offer_date, acceptance_date, join_date, decline_date: Date
- channel: String(50)
- channel_detail: String(200)
- evaluate_key: String(64)

用途: 候補者（応募者）情報。

---

## applications
- id: Integer PK
- org_id: Integer
- candidate_id: Integer FK -> candidates.id
- status: String(50) (default screening)
- stage: String(50) (default document)
- score_avg: Float
- last_evaluated_at: DateTime

用途: 候補者の応募単位（選考プロセス）。

---

## interviews
- id: Integer PK
- org_id: Integer
- candidate_id: Integer FK -> candidates.id (not null)
- step: String(20) (document/first/second/final)
- scheduled_at: DateTime
- status: String(20) (scheduled/done/no_show/canceled)
- result: String(20) (pass/fail/pending)
- comment: Text
- interviewer_id: Integer (ユーザID、任意)
- ai_score: Numeric(5,2) (任意)
- transcript_text: Text (最新版全文の冗長格納)
- rank, decision, interviewer (legacy/denormalized列)

用途: 面接（選考）の予定・結果を管理。

---

## recordings
- id: Integer PK
- org_id: Integer
- interview_id: Integer FK -> interviews.id (not null)
- storage_url: String(512) (録音ファイルの保存先 URL)
- duration_sec: Integer
- uploaded_by: Integer (user id)

用途: 面接に紐づく録音ファイルの管理。

---

## transcripts
- id: Integer PK
- org_id: Integer
- recording_id: Integer FK -> recordings.id (not null)
- text: Text (文字起こし全文)
- lang: String(10) (例: 'ja')
- status: String(20) (pending/processing/ok/error)
- error: Text (エラーメッセージ、nullable)
- utterances: JSON (話者分割/発話配列、Deepgram/whisper由来)
- metrics: JSON (speaking metrics の構造体)

用途: 録音の文字起こし出力と話者情報・解析メトリクスの保存。

---

## files
- id: Integer PK
- org_id: Integer FK -> organizations.id
- kind: String(20) (resume/audio/ics/other)
- storage_url: String(255)
- file_metadata: JSON (filename,size,content_type 等)
- created_at: DateTime (server_default now)
- candidate_id: Integer FK -> candidates.id (nullable)

用途: 各種ファイル（履歴書、録音、添付資料等）のメタ情報とストレージ参照。

---

## interview_evaluations
- id: Integer PK
- org_id: Integer
- interview_id: Integer FK -> interviews.id (not null)
- overall_score, speaking, logical, volume, honesty, proactive: Numeric(5,2)
- gpt_summary: Text
- raw_metrics: JSON
- audio_file_id: Integer FK -> files.id
- created_at: DateTime (server_default now)

用途: 面接ごとの評価レコード（AI/人間の評価を格納）。

---

## candidate_overall_evaluations
- id: Integer PK
- org_id: Integer
- candidate_id: Integer FK -> candidates.id (not null)
- version: Integer (default 1)
- aggregated_from: JSON (interview_evaluations.id の配列)
- overall_score, speaking, logical, volume, honesty, proactive: Numeric(5,2)
- gpt_summary: Text
- created_at: DateTime (server_default now)

用途: 候補者単位で複数面接の評価を集約した履歴。

---

## settings
- id: Integer PK
- org_id: Integer
- key: String(128)
- value: Text

用途: 組織単位のキー・バリューストア（ヒューリスティックやUI設定など）。

---

## notifications
- id: Integer PK
- org_id: Integer
- application_id: Integer FK -> applications.id
- type: String(50)
- sent_to: String(255)
- subject: String(255)
- body: Text
- provider_message_id: String(255)
- sent_at: DateTime

用途: 通知（メール等）送信ログ。

---

## sources
- id: Integer PK
- org_id: Integer
- name: String(120)

用途: 候補者の流入元マスタ。

---

### 注意事項
- 各 `OrgScopedMixin` は `org_id` を付与します。運用では `org_id` に基づくアクセス制御が期待されます。
- 実際の型や nullable 制約・インデックスはモデル定義を参照してください。DBマイグレーション（alembic）によりスキーマが変わる可能性があります。

---

作成日: 2025-08-20

このファイルを `docs/DB_SCHEMA.md` として保存しました。追加で以下が可能です：
- 各テーブルの ER 図（PlantUML / Mermaid）を生成
- カラムの nullable/デフォルト/インデックス情報を追記
- マイグレーション履歴（alembic）との対応表を作成

どれを進めますか？
