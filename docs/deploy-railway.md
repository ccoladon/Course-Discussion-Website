# Deploying to Railway

## Files Railway reads

All files are in the `site/` subdirectory. Set **Root Directory** to `site` in the Railway service settings.

- `site/runtime.txt` — Python version (e.g. `python-3.11.9`). Nixpacks picks this up.
- `site/requirements.txt` — installed during build.
- `site/Procfile` — start command.
- `site/railway.json` — declares the builder and overrides the start command + restart policy.

`site/Procfile` and `site/railway.json` carry the same start command — keep them in sync.

### Standard start command

```
python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

Migrations run on every deploy. `collectstatic` populates `STATIC_ROOT` so Whitenoise can serve it.

**Always bind gunicorn to `0.0.0.0:$PORT`.** Gunicorn's default is `127.0.0.1:8000`, which is only reachable inside the container — Railway's proxy can't route to it, so the generated domain returns 502 even after a "successful" build. Railway injects `$PORT`; the process must listen on it, on all interfaces.

### `site/railway.json` shape

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": { "builder": "NIXPACKS" },
  "deploy": {
    "startCommand": "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

## Database

Add a Postgres plugin to the Railway project. **Adding the plugin does not automatically share `DATABASE_URL` with your app service** — the plugin is a separate service that holds the variable. In the app service's **Variables**, add a reference:

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

(Replace `Postgres` with the Postgres service's exact name.) This resolves to the internal connection string (host `postgres.railway.internal`, reachable only inside Railway's network). Without it, settings falls back to the `localhost` default and `migrate` fails with "connection refused." `dj-database-url` consumes it directly in settings:

```python
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='postgresql://localhost/<dbname>'),
        conn_max_age=600,
    )
}
```

## TLS and proxy

Railway terminates TLS at its edge and forwards plain HTTP to the app. Two non-obvious settings:

```python
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False  # Railway already redirects http→https
```

Without `SECURE_PROXY_SSL_HEADER`, Django thinks every request is HTTP and `request.is_secure()` returns False, which breaks `CSRF_TRUSTED_ORIGINS` matching and `secure` cookies.

## Static files

```python
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
```

Add the Whitenoise middleware **right after** `SecurityMiddleware`:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # ... the rest
]
```

## Required env vars in Railway

Set these in the Railway service's Variables panel:

- `SECRET_KEY`
- `DEBUG` (set to `False` in prod)
- `ALLOWED_HOSTS` (comma-separated; include the Railway-assigned hostname)
- `CSRF_TRUSTED_ORIGINS` (full origins for prod)
- `SITE_URL` (used for building absolute links in emails)
- `DEFAULT_FROM_EMAIL`
- `RESEND_API_KEY`
- `ADMIN_NOTIFICATION_EMAIL`
- `DATABASE_URL` (reference the Postgres plugin: `${{Postgres.DATABASE_URL}}` — not auto-shared)
- `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_ENDPOINT_URL`, `R2_PUBLIC_URL` (for user-uploaded images — optional; leave unset to use local `media/`)

See `docs/secrets-and-env.md` for the full inventory and where each is configured.

## Production-only settings

```python
if not DEBUG:
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())
```

## Custom domain

Add the domain in Railway → Settings → Domains. Railway provisions a certificate via Let's Encrypt. Once active, add the domain to `ALLOWED_HOSTS` and add `https://<domain>` to `CSRF_TRUSTED_ORIGINS`.

## Reference files

- `site/railway.json`, `site/Procfile`, `site/runtime.txt`
- `site/config/settings.py` (TLS, static, security gates)
