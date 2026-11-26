# CLAUDE.md — Project orientation

Orientation for Claude Code sessions working in this repository. This file and
everything in `docs/` are project-agnostic; project-specific details (name,
API endpoints, domain rules, deployed resource names) live in `PROJECT.md`.

## Repo layout

```
PROJECT.md          # Project-specific details (name, endpoints, domain rules)
site/               # Django project (backend + website)
  config/            # Django project package: settings.py, urls.py
  core/              # Resend email backend, base utilities
  accounts/          # Auth: UserProfile, auto-signup, OTP, signals
  <main-app>/        # Main app: models, REST API, web views, templates
  templates/         # All templates (root-level, not per-app)
  static/            # Source static assets
  manage.py
  requirements.txt
  runtime.txt
  Procfile
  railway.json
app/                # Flutter mobile app (Android + iOS)
  lib/
    main.dart
    src/api/         # HTTP clients and API modules
    src/models/      # Data models
    src/screens/     # One file per screen
    src/widgets/     # Reusable widgets
    src/utils/       # Utility helpers
  android/
  ios/
  pubspec.yaml
docs/               # Documentation and architecture reference
```

## Stack

### Backend (site/)
- Django 5.1 · PostgreSQL · django-allauth (email OTP) · DRF · Whitenoise
- Resend HTTP API for email · Cloudflare R2 for images (or local media/ in dev)
- Tailwind via CDN · gunicorn · Railway for hosting

### Mobile (app/)
- Flutter + Material Design 3 · Dart
- `image_picker` for camera/gallery · `flutter_secure_storage` for auth tokens
- `provider` for state management · `http` for API calls
- `cached_network_image` for image loading · `share_plus` for sharing

## Local dev

```bash
# Backend (from the repo root)
python -m venv venv
source venv/bin/activate
pip install -r site/requirements.txt
cp .env.example .env            # fill in values
cd site
python manage.py migrate
python manage.py runserver

# Mobile (from the repo root, in a separate terminal)
cd app
flutter pub get
flutter run
```

## Settings conventions

- Env-driven via `python-decouple` (`config(...)`) in `site/config/settings.py`
- `DATABASE_URL` parsed by `dj-database-url` with `conn_max_age=600`
- `SECURE_PROXY_SSL_HEADER` + `SECURE_SSL_REDIRECT=False` (Railway terminates TLS)
- Whitenoise serves static via `CompressedManifestStaticFilesStorage`
- R2 for production images; local `media/` fallback in dev

## Auth conventions

- **Email OTP is the only auth method** — `ACCOUNT_LOGIN_BY_CODE_REQUIRED = True`
- Accounts auto-created on OTP request for unknown emails (see `site/accounts/api_views.py`)
- Flutter app uses token auth (`rest_framework.authtoken`) — token returned on code confirm
- Token stored in `flutter_secure_storage`, sent as `Authorization: Token <key>`

## API endpoints and domain rules

Project-specific endpoint lists and domain logic live in `PROJECT.md`.

## Deployment

Railway via Nixpacks with `ROOT_DIR=site`. See `docs/deploy-railway.md`.

## Working in this repo

- **Commit and push automatically** when a change is complete and verified
- **One concern per migration** — name them after what they do
- **Templates extend `base.html`** — Tailwind from CDN, no build step
- **Always ship a favicon** — SVG at `site/static/favicon.svg`
- **Notifications are fire-and-forget** — `fail_silently=True`

## Key docs

- `docs/stack.md` — versions and why each piece
- `docs/deploy-railway.md` — Railway specifics
- `docs/database-postgres.md` — DB conventions
- `docs/secrets-and-env.md` — env-var inventory
- `docs/cloudflare-r2.md` — R2 bucket setup
- `docs/flutter-apps.md` — Flutter conventions
