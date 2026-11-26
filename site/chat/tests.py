from channels.testing import WebsocketCommunicator
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.authtoken.models import Token

from chat.models import Message
from config.asgi import application
from core.testing import auth_client, make_user
from courses.models import Course, Enrollment, University


def _setup_course(university, code="CS 101", title="Intro to CS"):
    return Course.objects.create(university=university, code=code, title=title)


class ChatRESTTests(TestCase):
    def setUp(self):
        self.university = University.objects.create(
            name="Stanford University", slug="stanford", email_domains=["stanford.edu"]
        )
        self.course = _setup_course(self.university)
        self.section = self.course.default_section
        self.channel = self.section.channels.get(name="general")

        self.student = make_user("alice@stanford.edu", self.university)
        Enrollment.objects.create(user=self.student, section=self.section)
        self.client = auth_client(self.student)

        self.professor = make_user("prof@stanford.edu", self.university)
        self.professor.profile.role = "professor"
        self.professor.profile.save()
        self.section.professor = self.professor.profile
        self.section.save()
        Enrollment.objects.create(
            user=self.professor, section=self.section, role="professor"
        )
        self.prof_client = auth_client(self.professor)

    def test_post_and_list_messages(self):
        response = self.client.post(
            f"/api/channels/{self.channel.id}/messages/",
            {"body": "When is the first problem set due?"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["author"]["name"], "alice")

        listing = self.client.get(f"/api/channels/{self.channel.id}/messages/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data["results"]), 1)
        self.assertFalse(listing.data["has_more"])

    def test_mark_answer(self):
        message = Message.objects.create(
            channel=self.channel, author=self.student, body="How does recursion work?"
        )
        response = self.client.post(f"/api/messages/{message.id}/answer/")
        self.assertEqual(response.status_code, 200)
        message.refresh_from_db()
        self.assertTrue(message.is_answer)

    def test_student_cannot_pin(self):
        message = Message.objects.create(
            channel=self.channel, author=self.student, body="Pin me"
        )
        response = self.client.post(f"/api/messages/{message.id}/pin/")
        self.assertEqual(response.status_code, 403)

    def test_professor_can_pin(self):
        message = Message.objects.create(
            channel=self.channel, author=self.student, body="Exam moved to Friday"
        )
        response = self.prof_client.post(f"/api/messages/{message.id}/pin/")
        self.assertEqual(response.status_code, 200)
        message.refresh_from_db()
        self.assertTrue(message.is_pinned)

    def test_search_scoped_to_enrolled_courses(self):
        Message.objects.create(
            channel=self.channel, author=self.student, body="A monad is a monoid"
        )
        response = self.client.get("/api/search/", {"q": "monad"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["course_code"], "CS 101")

        outsider = make_user("bob@gmail.com", None, verified=True)
        outsider_client = auth_client(outsider)
        response = outsider_client.get("/api/search/", {"q": "monad"})
        self.assertEqual(response.data["results"], [])

    def test_non_member_cannot_read_channel(self):
        outsider = make_user("bob@gmail.com", None, verified=True)
        outsider_client = auth_client(outsider)
        response = outsider_client.get(f"/api/channels/{self.channel.id}/messages/")
        self.assertEqual(response.status_code, 403)

    def test_soft_deleted_messages_disappear_from_listing(self):
        message = Message.objects.create(
            channel=self.channel, author=self.student, body="oops"
        )
        response = self.client.delete(f"/api/messages/{message.id}/")
        self.assertEqual(response.status_code, 204)
        listing = self.client.get(f"/api/channels/{self.channel.id}/messages/")
        self.assertEqual(listing.data["results"], [])

    def test_professor_announcement_is_pinned(self):
        response = self.prof_client.post(
            f"/api/sections/{self.section.id}/announcements/",
            {"body": "Midterm moved to Friday"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data["message"]["is_pinned"])

    def test_student_cannot_announce(self):
        response = self.client.post(
            f"/api/sections/{self.section.id}/announcements/",
            {"body": "I'm the professor now"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


class ChatWebSocketTests(TransactionTestCase):
    def setUp(self):
        self.university = University.objects.create(
            name="Stanford University", slug="stanford", email_domains=["stanford.edu"]
        )
        self.course = _setup_course(self.university)
        self.section = self.course.default_section
        self.channel = self.section.channels.get(name="general")

        self.student = make_user("alice@stanford.edu", self.university)
        Enrollment.objects.create(user=self.student, section=self.section)
        self.token = Token.objects.create(user=self.student)

    async def test_message_broadcasts_over_websocket(self):
        communicator = WebsocketCommunicator(
            application,
            f"/ws/channels/{self.channel.id}/?token={self.token.key}",
            headers=[(b"origin", b"http://localhost")],
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_json_to({"type": "message", "body": "hello class"})
        response = await communicator.receive_json_from(timeout=5)
        self.assertEqual(response["type"], "message")
        self.assertEqual(response["message"]["body"], "hello class")

        await communicator.disconnect()

    async def test_anonymous_socket_is_rejected(self):
        communicator = WebsocketCommunicator(
            application,
            f"/ws/channels/{self.channel.id}/",
            headers=[(b"origin", b"http://localhost")],
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class WeeklyDigestTests(TestCase):
    def setUp(self):
        self.university = University.objects.create(
            name="Stanford University", slug="stanford", email_domains=["stanford.edu"]
        )
        self.course = _setup_course(self.university)
        self.section = self.course.default_section
        self.channel = self.section.channels.get(name="general")

        self.alice = make_user("alice@stanford.edu", self.university)
        self.bob = make_user("bob@stanford.edu", self.university)
        Enrollment.objects.create(user=self.alice, section=self.section)
        Enrollment.objects.create(user=self.bob, section=self.section)

    def test_digest_includes_unanswered_questions(self):
        Message.objects.create(
            channel=self.channel, author=self.bob, body="How do pointers work?"
        )
        call_command("send_weekly_digest", "--dry-run")
        call_command("send_weekly_digest")

        self.assertTrue(mail.outbox)
        bodies = "\n".join(message.body for message in mail.outbox)
        self.assertIn("How do pointers work?", bodies)

    def test_digest_skips_quiet_courses(self):
        call_command("send_weekly_digest")
        self.assertEqual(mail.outbox, [])
