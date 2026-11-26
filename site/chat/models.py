from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.text import sanitize_markdown


class Channel(models.Model):
    KIND_GENERAL = "general"
    KIND_ASSIGNMENTS = "assignments"
    KIND_EXAMS = "exams"
    KIND_PROJECTS = "projects"
    KIND_OFFTOPIC = "offtopic"
    KIND_CHOICES = [
        (KIND_GENERAL, "General"),
        (KIND_ASSIGNMENTS, "Assignments"),
        (KIND_EXAMS, "Exams"),
        (KIND_PROJECTS, "Projects"),
        (KIND_OFFTOPIC, "Off-topic"),
    ]

    DEFAULT_CHANNELS = [
        KIND_GENERAL,
        KIND_ASSIGNMENTS,
        KIND_EXAMS,
        KIND_PROJECTS,
        KIND_OFFTOPIC,
    ]

    section = models.ForeignKey(
        "courses.Section", on_delete=models.CASCADE, related_name="channels"
    )
    name = models.CharField(max_length=40)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_GENERAL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("section", "name")]
        ordering = ["section", "id"]

    def __str__(self) -> str:
        return f"#{self.name} ({self.section})"

    @property
    def course(self):
        return self.section.course


class Message(models.Model):
    channel = models.ForeignKey(
        Channel, on_delete=models.CASCADE, related_name="messages"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages"
    )
    body = models.TextField()
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
        help_text="Root message when this is a thread reply.",
    )
    is_pinned = models.BooleanField(default=False)
    is_answer = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["channel", "created_at"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self) -> str:
        return f"{self.author} in #{self.channel.name}: {self.body[:40]}"

    def save(self, *args, **kwargs):
        self.body = sanitize_markdown(self.body)
        super().save(*args, **kwargs)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    @property
    def is_thread_root(self) -> bool:
        return self.parent_id is None

    def can_be_moderated_by(self, user) -> bool:
        if user == self.author:
            return True
        from courses.permissions import can_moderate_section

        return can_moderate_section(user, self.channel.section)


class Reaction(models.Model):
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="reactions"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reactions"
    )
    emoji = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("message", "user", "emoji")]


class Report(models.Model):
    STATUS_OPEN = "open"
    STATUS_REVIEWED = "reviewed"
    STATUS_DISMISSED = "dismissed"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_REVIEWED, "Reviewed"),
        (STATUS_DISMISSED, "Dismissed"),
    ]

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_made"
    )
    reason = models.CharField(max_length=500)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("message", "reporter")]
        ordering = ["-created_at"]
