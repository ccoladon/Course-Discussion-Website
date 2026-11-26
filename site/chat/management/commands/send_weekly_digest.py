"""Weekly email digest: unanswered questions and pinned announcements.

Run from a Railway cron job:

    python manage.py send_weekly_digest
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from chat.models import Message


class Command(BaseCommand):
    help = "Email enrolled users their courses' unanswered questions and announcements."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=7, help="Lookback window (default 7).")
        parser.add_argument("--dry-run", action="store_true", help="Print instead of sending.")

    def handle(self, *args, **options):
        since = timezone.now() - timedelta(days=options["days"])
        dry_run = options["dry_run"]
        sent = 0

        users = (
            User.objects.filter(is_active=True, profile__is_verified=True)
            .select_related("profile")
            .prefetch_related("enrollments__section__course")
        )

        for user in users:
            enrollments = list(user.enrollments.all())
            if not enrollments:
                continue

            course_ids = [enrollment.section.course_id for enrollment in enrollments]
            course_names = {
                enrollment.section.course_id: enrollment.section.course.code
                for enrollment in enrollments
            }

            questions = (
                Message.objects.filter(
                    channel__section__course_id__in=course_ids,
                    parent__isnull=True,
                    deleted_at__isnull=True,
                    is_answer=False,
                    created_at__gte=since,
                )
                .exclude(author=user)
                .select_related("channel__section__course")
                .order_by("-created_at")[:5]
            )
            pinned = (
                Message.objects.filter(
                    channel__section__course_id__in=course_ids,
                    deleted_at__isnull=True,
                    is_pinned=True,
                    created_at__gte=since,
                )
                .select_related("channel__section__course")
                .order_by("-created_at")[:5]
            )

            if not questions and not pinned:
                continue

            lines = [f"Hi {user.profile.public_name},", "", "Here's what happened in your courses:"]
            if pinned:
                lines += ["", "Announcements"]
                for message in pinned:
                    lines.append(
                        f"- [{course_names[message.channel.section.course_id]}] {message.body[:200]}"
                    )
            if questions:
                lines += ["", "Unanswered questions"]
                for message in questions:
                    lines.append(
                        f"- [{course_names[message.channel.section.course_id]}] {message.body[:200]}"
                    )
            lines += ["", f"Open the app: {settings.SITE_URL}"]

            subject = "Your weekly course digest"
            if dry_run:
                self.stdout.write(f"--- {user.email} ---\n" + "\n".join(lines))
            else:
                send_mail(
                    subject=subject,
                    message="\n".join(lines),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            sent += 1

        self.stdout.write(self.style.SUCCESS(f"Digest prepared for {sent} user(s)."))
