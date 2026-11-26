import re

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from courses.models import University


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class OTPAuthTests(TestCase):
    def setUp(self):
        cache.clear()  # DRF throttle history lives in the shared cache.
        self.university = University.objects.create(
            name="Stanford University",
            slug="stanford",
            email_domains=["stanford.edu"],
        )
        self.client = APIClient()

    def _latest_code(self) -> str:
        body = mail.outbox[-1].body
        match = re.search(r"\b(\d{6})\b", body)
        self.assertIsNotNone(match, "OTP code missing from email body")
        return match.group(1)

    def test_full_login_flow(self):
        response = self.client.post(
            "/api/auth/request-code/", {"email": "Alice@Stanford.edu"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["verified_domain"])

        response = self.client.post(
            "/api/auth/confirm-code/",
            {"email": "alice@stanford.edu", "code": self._latest_code()},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.data)
        self.assertTrue(response.data["profile"]["is_verified"])

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
        me = self.client.get("/api/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["profile"]["university"], "Stanford University")

    def test_subdomain_matches_university(self):
        response = self.client.post(
            "/api/auth/request-code/", {"email": "bob@cs.stanford.edu"}, format="json"
        )
        self.assertTrue(response.data["verified_domain"])

    def test_unknown_domain_signs_in_unverified(self):
        response = self.client.post(
            "/api/auth/request-code/", {"email": "carol@gmail.com"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["verified_domain"])

    def test_wrong_code_is_rejected(self):
        self.client.post(
            "/api/auth/request-code/", {"email": "alice@stanford.edu"}, format="json"
        )
        response = self.client.post(
            "/api/auth/confirm-code/",
            {"email": "alice@stanford.edu", "code": "000000"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_resend_is_throttled(self):
        self.client.post(
            "/api/auth/request-code/", {"email": "alice@stanford.edu"}, format="json"
        )
        response = self.client.post(
            "/api/auth/request-code/", {"email": "alice@stanford.edu"}, format="json"
        )
        self.assertEqual(response.status_code, 429)
