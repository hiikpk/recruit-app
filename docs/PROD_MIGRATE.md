Production migration procedure

Purpose
- Provide a safe, repeatable procedure to apply Alembic migrations to production Postgres, with backup, SQL preview, and smoke checks.

Prerequisites
- The repository is checked out on a host with network access to production Postgres.
- Python virtualenv with alembic and project dependencies installed and the app's settings available (e.g., .env or environment variables).
- `pg_dump` and `pg_restore` (Postgres client tools) available on the host.
- `DATABASE_URL` environment variable set to the production Postgres URL, e.g.:

  export DATABASE_URL="postgresql://user:pass@host:5432/recruiting"

Steps (safe flow)

1) Backup (mandatory)
- Create a custom-format dump with `pg_dump` (this preserves ownership and can be restored with `pg_restore`).

  scripts/prod_migrate.sh will create a backup under /tmp/prod_db_backups by default.

2) SQL preview
- Generate the SQL Alembic would run (no changes applied):

  alembic upgrade --sql head > /tmp/alembic_upgrade_preview.sql

- Inspect the SQL for destructive statements (DROP TABLE, ALTER TABLE DROP COLUMN, CREATE TABLE, etc.).

3) Put app into maintenance (manual)
- Stop web and worker processes, or enable platform maintenance mode.

4) Apply migrations
- With processes stopped, run:

  scripts/prod_migrate.sh

  The script will ask for confirmation and then run `alembic upgrade head`.

5) Verify
- Check `alembic current --verbose` to see the applied revision.
- Run a couple smoke checks (health endpoint, list key table columns via psql).

6) Rollback (if needed)
- If migration caused a critical failure, restore from the backup produced in step 1:

  pg_restore --clean --if-exists --dbname="$DATABASE_URL" /tmp/prod_db_backups/recruiting-db-<TIMESTAMP>.dump

Notes
- Always keep backups off the app host (e.g., copy to secure storage) if possible.
- For high-traffic systems, prefer rolling upgrades and add migration steps that are backwards-compatible (avoid DROP COLUMN in the same release as code that still reads the column).

Contact
- If you want, I can run the script interactively with you or prepare a PR with a `maintenance` README section describing the exact commands for your hosting provider.
