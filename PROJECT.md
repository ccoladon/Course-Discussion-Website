# PROJECT.md — Course Discussion Website

Project-specific details. Architecture and conventions live in `CLAUDE.md`;
this file holds what is unique to this app.

## What it is

A course-scoped discussion site. Verified students join public chat rooms
grouped by course code and professor. The chat UI sits on a Q&A data model:
every message is threadable, searchable, and can be marked as an answer, so the
semester's questions become a durable course knowledge base.

**Locked product decisions**

- Visibility: verified students only (any school). Not readable by the public.
- Core model: chat UI over a Q&A data model.
- Rooms: a course-wide section plus per-professor sections nested under it.
- Course catalog starts empty; verified users create courses.
- School verification is by email-domain match.
- Auth is email OTP only; DRF tokens for API and WebSocket clients.

## Apps

| App | Contents |
|---|---|
| `accounts` | `UserProfile`, `EmailOTP`, OTP API, token issuance |
| `courses` | `University`, `Course`, `CourseAlias`, `Section`, `Enrollment` |
| `chat` | `Channel`, `Message`, `Reaction`, `Report`, REST API, WS consumer |
| `core` | Resend email backend, text normalisation/sanitising, test helpers |

## Domain rules

- **Verification.** A login email is matched against `University.email_domains`
  (subdomains allowed: `cs.stanford.edu` matches `stanford.edu`). Matching sets
  `UserProfile.is_verified = True` and assigns the university. Unverified users
  can sign in but cannot create or join courses.
- **Course identity.** `Course.code` is normalised (`cs101` → `CS 101`) and
  unique per university. `CourseAlias` rows let `COMPSCI 101` and
  `Intro to CS` resolve to the same course.
- **Sections.** Creating a course auto-creates a default course-wide section
  (`is_default=True`). Per-professor sections are added by staff.
- **Channels.** Every section gets `#general`, `#assignments`, `#exams`,
  `#projects`, `#offtopic` on creation.
- **Membership.** Access is course-level: enrolling in any section of a course
  grants read/write access to all of that course's sections.
- **Moderation.** The section professor, TAs, and staff can pin, delete, and
  post announcements. Authors can delete and mark their own questions answered.
- **Content.** Message bodies are stored as raw Markdown/LaTeX with all HTML
  escaped server-side. Clients render Markdown + KaTeX.
- **Deletion** is soft (`deleted_at`); deleted messages are hidden from listings
  and search.

## API endpoints

All under `/api/`. Token auth: `Authorization: Token <key>`.

```
POST /api/auth/request-code/          { email }
POST /api/auth/confirm-code/          { email, code } -> { token, profile }
POST /api/auth/logout/
GET  /api/me/                         profile + enrollments
PATCH /api/me/                        display_name

GET  /api/courses/search/?q=          alias-aware course search
POST /api/courses/                    { code, title, description? }
GET  /api/courses/<id>/
POST /api/courses/<id>/join/          { section_id? }
GET  /api/me/sections/                sections + channels
GET  /api/sections/<id>/channels/
POST /api/sections/<id>/claim/        request professor access (admin-approved)
POST /api/sections/<id>/announcements/ { body, email? }

GET  /api/channels/<id>/messages/?before=
POST /api/channels/<id>/messages/     { body, parent? }
GET  /api/messages/<id>/replies/
POST /api/messages/<id>/answer/       toggle answered
POST /api/messages/<id>/pin/          moderators only
DELETE /api/messages/<id>/            soft delete
GET  /api/search/?q=                  scoped to enrolled courses
POST /api/reports/                    { message, reason }

WS   /ws/channels/<id>/?token=<key>   {"type": "message", "body": "..."}
```

## Commands

```bash
python manage.py add_school "Stanford University" stanford.edu cs.stanford.edu
python manage.py seed_demo
python manage.py send_weekly_digest [--days 7] [--dry-run]
```

`send_weekly_digest` is designed to run as a Railway cron job.

## Deployment notes

- **daphne**, not gunicorn — Channels needs ASGI. Start command is in
  `site/Procfile` and `site/railway.json`.
- Add a **Redis** plugin and set `REDIS_URL` for cross-process WebSocket fan-out.
  Without it, the channel layer is in-memory (single process only).
- Local dev with no `DATABASE_URL` uses SQLite.
