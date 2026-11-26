# Course Discussion Website

Verified students join public chat rooms grouped by course and professor.
Chat UI, Q&A data model: threads, mark-as-answer, search, and professor
announcements.

## Quick start

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r site/requirements.txt

cp .env.example .env        # optional; dev defaults work without it
cd site
python manage.py migrate
python manage.py add_school "Stanford University" stanford.edu
python manage.py createsuperuser
python manage.py runserver
```

Open http://localhost:8000 for the landing page, `/admin/` for the admin, and
`/api/` for the API.

Without `DATABASE_URL` the app uses SQLite; without `REDIS_URL` the channel
layer is in-memory (fine for local dev). Without `RESEND_API_KEY`, OTP emails
are printed to the server log.

## Tests

```bash
cd site
python manage.py test
```

## Docs

- `PROJECT.md` — domain rules, API surface, commands
- `CLAUDE.md` — repo conventions and layout
- `docs/` — stack, deployment, secrets, R2, Flutter conventions
