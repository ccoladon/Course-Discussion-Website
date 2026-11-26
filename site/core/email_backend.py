"""Resend HTTP API email backend.

Implements Django's standard email backend interface so ``send_mail()`` works
unchanged. Falls back to printing to stdout when ``RESEND_API_KEY`` is unset,
which keeps local development and tests free of network calls.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

RESEND_ENDPOINT = "https://api.resend.com/emails"


class ResendEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        if not settings.RESEND_API_KEY:
            for message in email_messages:
                logger.info(
                    "[email:console] to=%s subject=%r\n%s",
                    message.to,
                    message.subject,
                    message.body,
                )
            return len(email_messages)

        sent = 0
        for message in email_messages:
            try:
                self._send_one(message)
                sent += 1
            except Exception:
                logger.exception("Resend delivery failed for %s", message.to)
                if not self.fail_silently:
                    raise
        return sent

    def _send_one(self, message) -> None:
        payload = {
            "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
            "to": list(message.to),
            "subject": message.subject,
            "text": message.body,
        }
        if message.cc:
            payload["cc"] = list(message.cc)
        if message.bcc:
            payload["bcc"] = list(message.bcc)
        if message.reply_to:
            payload["reply_to"] = list(message.reply_to)

        # Multipart HTML mail: send the HTML body when one is present.
        for content, mimetype in getattr(message, "alternatives", []):
            if mimetype == "text/html":
                payload["html"] = content
                break

        response = requests.post(
            RESEND_ENDPOINT,
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        response.raise_for_status()
