from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os

# this is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# Configure logging only if the config contains logging sections
try:
    if getattr(config, "config_file_name", None):
        fileConfig(config.config_file_name)
except Exception:
    # Logging config is optional; ignore if not present
    pass

# Import Flask SQLAlchemy metadata
# Ensure app package is importable and models are loaded so tables are registered on metadata
from app.extensions import db  # type: ignore
from app import models  # noqa: F401  # ensure model modules are imported
from config import Config

# Use the metadata from Flask-SQLAlchemy models for autogenerate
target_metadata = db.metadata

# Resolve DB URL: env > Config > default, and fix relative sqlite path to instance folder
cfg_url = os.getenv('DATABASE_URL', Config.SQLALCHEMY_DATABASE_URI)
if cfg_url.startswith('sqlite:///') and not cfg_url.startswith('sqlite:////'):
    # relative sqlite path -> point to instance folder
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    instance_dir = os.path.join(root_dir, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    rel_path = cfg_url.replace('sqlite:///','',1)
    abs_path = os.path.join(instance_dir, rel_path)
    url = f'sqlite:///{abs_path.replace(os.sep, "/")}'
else:
    url = cfg_url

def run_migrations_offline():
    context.configure(url=url, literal_binds=True, target_metadata=target_metadata, compare_type=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        {"sqlalchemy.url": url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()