from __future__ import annotations

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class UserProfile(models.Model):
    ROLE_STUDENT = "student"
    ROLE_TA = "ta"
    ROLE_PROFESSOR = "professor"
    ROLE_ALUM = "alum"
    ROLE_CHOICES = [
        (ROLE_STUDENT, "Student"),
        (ROLE_TA, "TA"),
        (ROLE_PROFESSOR, "Professor"),
        (ROLE_ALUM, "Alum"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    university = models.ForeignKey(
        "courses.University",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="True once the account's email domain matched a university.",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    display_name = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.display_name or self.user.email or self.user.username

    @property
    def public_name(self) -> str:
        if self.display_name:
            return self.display_name
        local = (self.user.email or self.user.username).split("@")[0]
        return local


class EmailOTP(models.Model):
    """A one-time login code. Only the hash is stored."""

    email = models.EmailField(db_index=True)
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="otps"
    )
    code_hash = models.CharField(max_length=128)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"OTP for {self.email}"

    # -- creation ---------------------------------------------------------

    @classmethod
    def create_for(cls, email: str, user: User | None = None) -> tuple["EmailOTP", str]:
        code = f"{secrets.randbelow(1_000_000):06d}"
        otp = cls.objects.create(
            email=email,
            user=user,
            code_hash=make_password(code),
            expires_at=timezone.now() + timedelta(seconds=settings.OTP_TTL_SECONDS),
        )
        return otp, code

    # -- validation -------------------------------------------------------

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def verify(self, code: str) -> bool:
        if self.consumed_at or self.is_expired:
            return False
        if self.attempts >= settings.OTP_MAX_ATTEMPTS:
            return False

        self.attempts += 1
        matched = check_password(code.strip(), self.code_hash)
        if matched:
            self.consumed_at = timezone.now()
        self.save(update_fields=["attempts", "consumed_at"])
        return matched

    @classmethod
    def latest_for(cls, email: str) -> "EmailOTP | None":
        return cls.objects.filter(email=email).first()

    @classmethod
    def can_resend(cls, email: str) -> bool:
        latest = cls.latest_for(email)
        if latest is None:
            return True
        elapsed = (timezone.now() - latest.created_at).total_seconds()
        return elapsed >= settings.OTP_RESEND_SECONDS
