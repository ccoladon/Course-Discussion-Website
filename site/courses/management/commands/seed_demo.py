"""Seed a demo school, users, course, and chat history.

    python manage.py seed_demo

Idempotent: safe to run more than once.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from chat.models import Channel, Message
from courses.models import Course, CourseAlias, Enrollment, Section, University


class Command(BaseCommand):
    help = "Create a demo university, users, course, and sample messages."

    def handle(self, *args, **options):
        university, _ = University.objects.get_or_create(
            name="Demo University",
            defaults={"email_domains": ["demo.edu"]},
        )
        if "demo.edu" not in university.email_domains:
            university.email_domains = university.email_domains + ["demo.edu"]
            university.save(update_fields=["email_domains"])

        alice = self._user("alice@demo.edu", university, "Alice Chen")
        bob = self._user("bob@demo.edu", university, "Bob Patel")
        professor = self._user(
            "prof@demo.edu", university, "Dr. Alvarez", role="professor"
        )

        course, _ = Course.objects.get_or_create(
            university=university,
            code="CS 101",
            defaults={
                "title": "Intro to Computer Science",
                "description": "Algorithms, recursion, and data structures.",
            },
        )
        CourseAlias.objects.get_or_create(course=course, alias="COMPSCI 101")

        default_section = course.default_section
        section, _ = Section.objects.get_or_create(
            course=course,
            term="Fall 2026",
            section_code="002",
            defaults={"professor": professor.profile},
        )
        if section.professor_id != professor.profile.id:
            section.professor = professor.profile
            section.save(update_fields=["professor"])

        Enrollment.objects.get_or_create(user=alice, section=default_section)
        Enrollment.objects.get_or_create(user=bob, section=default_section)
        Enrollment.objects.get_or_create(
            user=professor, section=section, defaults={"role": Enrollment.ROLE_PROFESSOR}
        )

        general = default_section.channels.get(name="general")
        assignments = default_section.channels.get(name="assignments")
        prof_general = section.channels.get(name="general")

        if not general.messages.exists():
            welcome = Message.objects.create(
                channel=general,
                author=alice,
                body="Welcome to **CS 101**! Ask questions here — if your question "
                "gets answered, mark it so it's easy to find later.",
            )
            Message.objects.create(
                channel=general,
                author=professor,
                body="Office hours are Tue/Thu 2–4pm in Gates 104. I'll post "
                "announcements here too.",
            )
            question = Message.objects.create(
                channel=general,
                author=bob,
                body="How do I know when a recursive function will terminate?",
            )
            Message.objects.create(
                channel=general,
                author=professor,
                body="Every recursive call must move toward a **base case**. "
                "If the input doesn't shrink each time, you'll recurse forever.",
                parent=question,
            )
            question.is_answer = True
            question.save(update_fields=["is_answer"])

            Message.objects.create(
                channel=assignments,
                author=bob,
                body="For problem 3, is the running time $O(n \\log n)$ or "
                "$O(n^2)$? The recurrence is $T(n) = 2T(n/2) + O(n)$.",
            )

        if not prof_general.messages.exists():
            Message.objects.create(
                channel=prof_general,
                author=professor,
                body="**Midterm moved to Friday.** Review chapters 4–6 and the "
                "recursion practice set.",
                is_pinned=True,
            )

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write("")
        self.stdout.write("  Sign in at:  http://localhost:8000/login/")
        self.stdout.write("  Student:     alice@demo.edu")
        self.stdout.write("  Professor:   prof@demo.edu")
        self.stdout.write("")
        self.stdout.write(
            "  With no RESEND_API_KEY set, the 6-digit code is printed in the "
            "server log."
        )

    def _user(self, email, university, display_name, role="student"):
        user, created = User.objects.get_or_create(
            username=email, defaults={"email": email}
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        profile = user.profile
        profile.university = university
        profile.is_verified = True
        profile.display_name = display_name
        profile.role = role
        profile.save()
        return user
