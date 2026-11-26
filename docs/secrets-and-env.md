# Secrets and environment variables

## Inventory

All env vars are read via `python-decouple`'s `config('NAME', default=...)` in `site/config/settings.py`:

| Variable | Purpose | Local | Production (Railway) |
|---|---|---|---|
| `SECRET_KEY` | Django session/CSRF signing key | `.env` | Railway Variables |
| `DEBUG` | Toggles Django debug mode | `.env` (`True`) | Railway Variables (`False`) |
| `ALLOWED_HOSTS` | CSV of hostnames Django will serve | `.env` | Railway Variables |
| `CSRF_TRUSTED_ORIGINS` | CSV of full origins for CSRF | unset | Railway Variables |
| `DATABASE_URL` | Postgres connection string | `.env` | Reference the Postgres plugin (`${{Postgres.DATABASE_URL}}`) |
| `SITE_URL` | Used to build absolute links in emails | `.env` | Railway Variables |
| `DEFAULT_FROM_EMAIL` | `From:` header for outbound mail | `.env` | Railway Variables |
| `RESEND_API_KEY` | Resend HTTP API key | `.env` | Railway Variables |
| `ADMIN_NOTIFICATION_EMAIL` | Recipient for admin notifications | `.env` | Railway Variables |
| `R2_ACCESS_KEY_ID` | Cloudflare R2 access key | `.env` (or unset) | Railway Variables |
| `R2_SECRET_ACCESS_KEY` | Cloudflare R2 secret key | `.env` (or unset) | Railway Variables |
| `R2_BUCKET_NAME` | R2 bucket name | `.env` (or unset) | Railway Variables |
| `R2_ENDPOINT_URL` | R2 S3-compatible endpoint URL | `.env` (or unset) | Railway Variables |
| `R2_PUBLIC_URL` | Custom domain for public image URLs | `.env` (or unset) | Railway Variables |
| `CORS_ALLOWED_ORIGINS` | Allowed origins for CORS | `.env` | Railway Variables |

## Rules

- **`.env` is gitignored** (lives at repo root, shared by both `site/` and `app/`).
- **Never commit secret values.** That includes `.mcp.json`, `tbls.yml`, deployment configs.
- **Always reference secrets via env vars.**
- **Ship a `.env.example`** at the repo root with the variable names and dummy values.
- **Use `python-decouple` defaults** to keep dev frictionless.

## Pattern: settings.py

```python
from decouple import config, Csv

SECRET_KEY = config('SECRET_KEY', default='insecure-dev-key-change-in-production')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
```

## Pattern: `.env.example` (at repo root)

```
SECRET_KEY=replace-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://localhost/<dbname>
CSRF_TRUSTED_ORIGINS=
SITE_URL=http://localhost:8000
DEFAULT_FROM_EMAIL=noreply@example.com
RESEND_API_KEY=
ADMIN_NOTIFICATION_EMAIL=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
R2_ENDPOINT_URL=
R2_PUBLIC_URL=
CORS_ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

R2 vars can stay empty in local dev — the app falls back to local `media/` storage when `R2_ACCESS_KEY_ID` is unset.
