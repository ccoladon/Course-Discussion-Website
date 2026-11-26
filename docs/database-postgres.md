# Database (PostgreSQL)

## Postgres only — even in dev

Use Postgres locally too. Spin up a local Postgres any way you like (Homebrew, Docker, Postgres.app) and point `DATABASE_URL` at it in `.env` (at the repo root):

```
DATABASE_URL=postgresql://localhost/<dbname>
```

## Connection config

```python
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='postgresql://localhost/<dbname>'),
        conn_max_age=600,
    )
}
```

`conn_max_age=600` keeps connections open for 10 minutes — cheap latency win.

## Parsing `DATABASE_URL` for psql / pg_dump

Standard `psql` and `pg_dump` don't accept a single URL when you want to interleave flags. Use the `dburl_to_pgvars.sh` script to fan the URL out into `PG*` env vars:

```bash
source dburl_to_pgvars.sh
psql                                  # connects with PG* vars
pg_dump --no-owner --no-acl > dump.sql
```

⚠️ Don't commit dumps. Add `*.sql` to `.gitignore`.

## Schema docs with `tbls`

[`tbls`](https://github.com/k1LoW/tbls) generates a Markdown + SVG reference for every table. Config in `tbls.yml`:

```yaml
dsn: ${DATABASE_URL}
docPath: dbdoc
```

## Migrations

- One concern per migration. Name them after what they do.
- Data migrations live alongside schema migrations.
- Migrations run automatically on every Railway deploy (see `site/Procfile`).

## Reference files

- `site/config/settings.py` — `DATABASES` block
- `dburl_to_pgvars.sh` — URL → PG* vars
- `tbls.yml` — schema-doc config
- `site/accounts/migrations/` — auth migrations
- `site/<main-app>/migrations/` — main-app migrations
