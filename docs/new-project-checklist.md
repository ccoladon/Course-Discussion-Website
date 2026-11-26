# New project bootstrap checklist

Step-by-step for spinning up a new repo on this stack. Each step links to the doc that explains the pattern in more depth.

## 1. Repo skeleton

- [ ] `git init` and create the GitHub repo.
- [ ] `.gitignore` covering Python, envs, Django, Flutter, OS noise, and DB dumps.
- [ ] `README.md` with a one-line description.

## 2. Pin Python and dependencies

- [ ] `site/runtime.txt` → `python-3.11.9`.
- [ ] `site/requirements.txt` with all needed packages.
- [ ] `python -m venv venv && source venv/bin/activate && pip install -r site/requirements.txt`.

## 3. Create the Django project

- [ ] `django-admin startproject config site/`
- [ ] Move secrets/config in `site/config/settings.py` to env-driven via `python-decouple` + `dj-database-url`.
- [ ] Set `STATIC_ROOT`, `STATICFILES_DIRS`, and `STORAGES['staticfiles']` for Whitenoise.
- [ ] Add `SECURE_PROXY_SSL_HEADER` and the `if not DEBUG:` security block.
- [ ] Add `'whitenoise.middleware.WhiteNoiseMiddleware'` right after `SecurityMiddleware`.
- [ ] Add DRF, CORS headers, and auth token settings.

→ Details: [`docs/deploy-railway.md`](deploy-railway.md), [`docs/secrets-and-env.md`](secrets-and-env.md)

## 4. Local env

- [ ] `.env` with values from your `.env.example` template at the repo root.
- [ ] `.env.example` checked in.
- [ ] Local Postgres up, `DATABASE_URL` points at it.
- [ ] `python manage.py migrate && python manage.py runserver` boots cleanly (run from `site/`).

## 5. Auth (allauth + OTP)

- [ ] Add `'django.contrib.sites'`, `'allauth'`, `'allauth.account'` to `INSTALLED_APPS` in `site/config/settings.py`.
- [ ] Add `'allauth.account.middleware.AccountMiddleware'`.
- [ ] `SITE_ID = 1`. Configure the Site row in admin.
- [ ] Enable OTP: `ACCOUNT_LOGIN_BY_CODE_REQUIRED = True`.
- [ ] Set `ACCOUNT_LOGIN_METHODS = {'email'}`, `ACCOUNT_SIGNUP_FIELDS = ['email*']`.
- [ ] (Only if you will have a mobile/API client.) Create API auth endpoints in `accounts/api_views.py` for mobile token auth.

## 6. `core` app + Resend email backend

- [ ] `python manage.py startapp core` from `site/`.
- [ ] Copy `site/core/email_backend.py` (Resend HTTP backend).
- [ ] `EMAIL_BACKEND = 'core.email_backend.ResendEmailBackend'`.

## 7. UserProfile

- [ ] `accounts` app with a `UserProfile` model `OneToOneField(User)`.
- [ ] `post_save` signal on `User` to auto-create the profile.
- [ ] `apps.py` → `def ready(self): from . import signals` to connect.

## 8. Main app

- [ ] Create the project's main app with models, web views, and admin (add serializers/API views only if you will have a client).
- [ ] Wire URLs in `site/config/urls.py`.
- [ ] Put project-specific endpoints and domain rules in `PROJECT.md`.

## 9. Templates

- [ ] `site/templates/base.html` with Tailwind CDN load.
- [ ] `TEMPLATES[0]['DIRS'] = [BASE_DIR / 'templates']`.
- [ ] One subdir per app under `site/templates/<app>/`.

## 10. Railway deploy

- [ ] Create Railway project, link to the GitHub repo.
- [ ] Set **Root Directory** to `site` in Railway service settings.
- [ ] Add the Postgres plugin.
- [ ] Set env vars: `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, etc.
- [ ] Commit `site/Procfile` and `site/railway.json`.
- [ ] Push. Railway builds via Nixpacks.

→ Details: [`docs/deploy-railway.md`](deploy-railway.md)

## 11. Cloudflare DNS

- [ ] Add the site to Cloudflare (see [cloudflare-dns.md](cloudflare-dns.md)).
- [ ] Disable DNSSEC at the registrar, replace nameservers with Cloudflare's.
- [ ] Add DNS records (apex CNAME with orange cloud for Railway).
- [ ] Add the domain to Railway → Settings → Domains.

→ Details: [`docs/cloudflare-dns.md`](cloudflare-dns.md)

## 12. Cloudflare R2 (optional)

- [ ] Create an R2 bucket for user-uploaded media.
- [ ] Wire the `STORAGES` switch in `settings.py`.

→ Details: [`docs/cloudflare-r2.md`](cloudflare-r2.md)

## 13. CLAUDE.md and PROJECT.md

- [ ] Copy `CLAUDE.md` and `docs/` from the template unchanged.
- [ ] Create `PROJECT.md` with the project's name, API endpoints, domain rules, and deployed resource names.

---

# Flutter app bootstrap

## 1. Create the project

- [ ] `flutter create --project-name <name> --org com.<yourdomain> app/`

## 2. Dependencies

Add to `app/pubspec.yaml`:
```yaml
dependencies:
  http: ^1.6.0
  image_picker: ^1.1.0
  path_provider: ^2.1.6
  intl: ^0.20.3
  geolocator: ^14.0.2
  flutter_secure_storage: ^9.2.0
  cached_network_image: ^3.4.0
  provider: ^6.1.0
  share_plus: ^10.0.0
```

- [ ] `flutter pub get` — run from `app/`.

## 3. App structure

Create under `app/lib/`:
- `main.dart` — app entry point, Provider setup, MaterialApp routes
- `src/api/client.dart` — HTTP client with auth token handling
- `src/screens/` — one file per screen (home, auth, upload, detail, search, profile)
- `src/widgets/` — reusable widgets

## 4. Build verification

- [ ] `flutter analyze` — catches type errors, dead code
- [ ] `flutter build apk --debug` — verifies Android build
- [ ] `flutter build ios --no-codesign` — verifies iOS build

→ Details: [`docs/flutter-apps.md`](flutter-apps.md)
