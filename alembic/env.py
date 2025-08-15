# alembic/env.py
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
import os, sys, pathlib

os.environ["SKIP_CREATE_ALL"] = "1"

# 1) プロジェクトルートを import パスに
BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 2) Alembic 設定・ロギング
config = context.config
try:
    if getattr(config, "config_file_name", None):
        fileConfig(config.config_file_name)
except Exception:
    pass

# 3) wsgi から app を、extensions から db を取る（←ここが修正点）
from wsgi import app                  # wsgi.py は app を公開している前提
from app.extensions import db         # db は extensions 側から import

# 4) アプリ設定から URL を取得し、モデルを読み込んで metadata を確定
with app.app_context():
    url = os.getenv("DATABASE_URL") or app.config.get("SQLALCHEMY_DATABASE_URI")

    # 相対 sqlite パス対策（任意）
    if url and url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        instance_dir = BASE_DIR / "instance"
        instance_dir.mkdir(parents=True, exist_ok=True)
        rel_path = url.replace("sqlite:///", "", 1)
        url = f"sqlite:///{(instance_dir / rel_path).as_posix()}"

    # モデルを import して metadata に登録
    import app.models  # noqa: F401

    target_metadata = db.metadata

def run_migrations_offline():
    context.configure(url=url, target_metadata=target_metadata,
                      literal_binds=True, compare_type=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config({"sqlalchemy.url": url},
                                     prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          compare_type=True, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
