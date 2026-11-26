from django.test import TestCase

from chat.models import Channel
from core.testing import auth_client, make_user
from courses.models import Course, CourseAlias, Enrollment, University


class CourseTests(TestCase):
    def setUp(self):
        self.university = University.objects.create(
            name="Stanford University", slug="stanford", email_domains=["stanford.edu"]
        )
        self.user = make_user("alice@stanford.edu", self.university)
        self.client = auth_client(self.user)

    def test_create_course_builds_default_section_and_channels(self):
        response = self.client.post(
            "/api/courses/",
            {"code": "cs101", "title": "Intro to Computer Science"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

        course = Course.objects.get(code="CS 101")
        self.assertEqual(course.university, self.university)

        section = course.default_section
        self.assertIsNotNone(section)
        self.assertEqual(section.channels.count(), len(Channel.DEFAULT_CHANNELS))
        self.assertTrue(Enrollment.objects.filter(user=self.user, section=section).exists())

    def test_duplicate_course_code_is_rejected(self):
        Course.objects.create(university=self.university, code="CS 101", title="Intro")
        response = self.client.post(
            "/api/courses/", {"code": "CS-101", "title": "Again"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_search_matches_code_and_alias(self):
        course = Course.objects.create(
            university=self.university, code="CS 101", title="Intro to CS"
        )
        CourseAlias.objects.create(course=course, alias="COMPSCI 101")
        CourseAlias.objects.create(course=course, alias="Intro to CS")

        for query in ("CS101", "cs-101", "COMPSCI 101", "Intro to CS"):
            response = self.client.get("/api/courses/search/", {"q": query})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data), 1, query)
            self.assertEqual(response.data[0]["code"], "CS 101")

    def test_join_course(self):
        course = Course.objects.create(
            university=self.university, code="CS 101", title="Intro to CS"
        )
        response = self.client.post(f"/api/courses/{course.id}/join/", {}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            Enrollment.objects.filter(user=self.user, section__course=course).exists()
        )

    def test_unverified_user_cannot_join(self):
        outsider = make_user("bob@gmail.com", None, verified=False)
        client = auth_client(outsider)
        course = Course.objects.create(
            university=self.university, code="CS 101", title="Intro to CS"
        )
        response = client.post(f"/api/courses/{course.id}/join/", {}, format="json")
        self.assertEqual(response.status_code, 403)
