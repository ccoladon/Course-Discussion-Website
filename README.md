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
python manage.py seed_demo   # demo school, users, course, and chat history
python manage.py runserver
```

Open **http://localhost:8000/login/** and sign in as `alice@demo.edu`
(student) or `prof@demo.edu` (professor).

With no `RESEND_API_KEY` set, the 6-digit code is printed in the server
terminal:

```
[email:console] to=['alice@demo.edu'] subject='Your Course Chat sign-in code'
Your sign-in code is 123456. It expires in 10 minutes.
```

Other useful URLs: `/` landing page, `/app/` chat client, `/admin/` Django admin,
`/api/` API.

Without `DATABASE_URL` the app uses SQLite; without `REDIS_URL` the channel
layer is in-memory (fine for local dev).

## Tests

```bash
cd site
python manage.py test
```

## Docs

- `PROJECT.md` — domain rules, API surface, commands
- `CLAUDE.md` — repo conventions and layout
- `docs/` — stack, deployment, secrets, R2, Flutter conventions
