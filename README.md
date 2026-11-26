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

## Share it on your local network

1. Find your LAN address: `ipconfig getifaddr en0` (e.g. `192.168.1.50`).
2. Add it to `.env`:

   ```dotenv
   ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.50
   CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,http://192.168.1.50:8000
   OTP_DEV_ECHO=True
   ```

3. Run the server on all interfaces:

   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

4. Other devices on the same Wi-Fi open `http://192.168.1.50:8000/login/`.

`OTP_DEV_ECHO=True` fills the login code in automatically (it is also gated on
`DEBUG`), so people on the network can sign in without reading your terminal.
This is a development server — never expose it to the internet.

## Tests

```bash
cd site
python manage.py test
```

## Docs

- `PROJECT.md` — domain rules, API surface, commands
- `CLAUDE.md` — repo conventions and layout
- `docs/` — stack, deployment, secrets, R2, Flutter conventions
