# Stack

This template supports two kinds of project — pick the one that fits.

## Django web apps

The reusable technology baseline for a Django project built on this template.

## Flutter mobile apps

See [`docs/flutter-apps.md`](flutter-apps.md).

## Versions

### Django stack

| Layer | Choice | Pin location |
|---|---|---|
| Language | Python 3.11 | `site/runtime.txt` |
| Web framework | Django 5.0–5.1 | `site/requirements.txt` |
| Database driver | `psycopg2-binary` | `site/requirements.txt` |
| Database | PostgreSQL (managed in prod) | Railway plugin |
| Auth | `django-allauth[socialaccount]` | `site/requirements.txt` |
| DB URL parsing | `dj-database-url` | `site/requirements.txt` |
| Settings/env | `python-decouple` | `site/requirements.txt` |
| WSGI server | `gunicorn` | `site/requirements.txt` |
| Static files | `whitenoise` | `site/requirements.txt` |
| Image fields | `Pillow` | `site/requirements.txt` |
| HTTP client | `requests` (for Resend) | `site/requirements.txt` |
| CSS | Tailwind via CDN | `site/templates/base.html` |
| Email | Resend HTTP API | `site/core/email_backend.py` |
| User images | Cloudflare R2 (S3-compatible) | `site/requirements.txt` → `django-storages[s3]` |
| DNS | Cloudflare (nameservers) | Domain registrar → Cloudflare |
| Hosting | Railway (Nixpacks) | `site/railway.json` |

### Flutter stack

| Layer | Choice | Pin location |
|---|---|---|
| Language | Dart (via Flutter SDK) | `pubspec.yaml` → `environment.sdk` |
| UI framework | Flutter + Material Design | `pubspec.yaml` → `flutter` |
| HTTP client | `package:http` | `pubspec.yaml` → dependencies |
| Locale/time | `package:intl` + `package:timezone` | `pubspec.yaml` → dependencies |
| Location | `package:geolocator` | `pubspec.yaml` → dependencies |
| File storage | `package:path_provider` | `pubspec.yaml` → dependencies |
| Android build | Kotlin DSL, AGP 9, Gradle 9 | `android/*.gradle.kts` |
| iOS build | Xcode, CocoaPods | `ios/Podfile`, `ios/Runner.xcodeproj/` |

Full details in [`docs/flutter-apps.md`](flutter-apps.md).

## Why each piece (Django stack)

Pins are loose (`>=`/`<`) rather than exact. Reproducibility comes from `site/runtime.txt` + Railway's Nixpacks cache, not a lockfile.

- **Resend (not SMTP).** A custom HTTP backend (`site/core/email_backend.py`) avoids SMTP configuration entirely. It accepts the standard Django `EmailMessage` interface, so `send_mail()` works unchanged.
- **Tailwind CDN (not a build step).** `<script src="https://cdn.tailwindcss.com">` in `site/templates/base.html`. No node, no PostCSS, no asset pipeline. Trade-off: bigger CSS payload; acceptable for low-traffic sites.
- **allauth for both OTP and OAuth.** One library, one configuration block, one set of templates. Lets you ship passwordless auth without writing custom views.
- **Whitenoise.** Serves static files directly from gunicorn — no separate static host or CDN required. `CompressedManifestStaticFilesStorage` gives content-hashed filenames + gzip/brotli.
- **`python-decouple` + `dj-database-url`.** Decouple reads `.env` locally and env vars in prod with the same `config('NAME', default=...)` call. `dj-database-url` parses `DATABASE_URL` into Django's `DATABASES` dict in one line.
- **Railway Nixpacks.** Auto-detects Python from `site/runtime.txt`, runs `pip install -r site/requirements.txt`, executes `site/Procfile`. Zero build config in repo beyond the two files.
- **Cloudflare R2 for user uploads.** S3-compatible, zero egress fees, served through Cloudflare's network. `django-storages[s3]` provides the `StorageBackend`; the fallback to local `site/media/` in dev means no Cloudflare credentials needed to run the app locally.
- **Cloudflare DNS.** Free DNS hosting with CNAME flattening (apex domains can use CNAMEs when proxied), DDoS protection, and automatic SSL. The domain stays registered at any registrar; only the nameservers point at Cloudflare.

## Reference files

- `site/requirements.txt` — package list
- `site/runtime.txt` — Python version
- `site/config/settings.py` — every choice above is wired here
- `site/core/email_backend.py` — Resend backend implementation
- `site/templates/base.html` — Tailwind CDN load + design tokens
- `docs/cloudflare-r2.md` — R2 bucket setup, credentials, local vs prod
- `docs/cloudflare-dns.md` — DNS setup, nameservers, Railway domain
