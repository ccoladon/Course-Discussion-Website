from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from core.text import normalize_course_code


class University(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    email_domains = models.JSONField(
        default=list,
        blank=True,
        help_text='Email domains that verify as this school, e.g. ["stanford.edu"].',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "universities"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        self.email_domains = [
            d.strip().lower().lstrip("@") for d in (self.email_domains or []) if d.strip()
        ]
        super().save(*args, **kwargs)

    @classmethod
    def for_email(cls, email: str) -> "University | None":
        """Match an email to a university, allowing subdomains.

        ``cs.stanford.edu`` matches a ``stanford.edu`` entry.
        """
        if "@" not in email:
            return None
        domain = email.rsplit("@", 1)[1].strip().lower()
        for university in cls.objects.all():
            for allowed in university.email_domains:
                if domain == allowed or domain.endswith("." + allowed):
                    return university
        return None


class Course(models.Model):
    university = models.ForeignKey(
        University, on_delete=models.CASCADE, related_name="courses"
    )
    code = models.CharField(max_length=30, help_text="Normalised, e.g. 'CS 101'.")
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("university", "code")]
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.title}"

    def save(self, *args, **kwargs):
        self.code = normalize_course_code(self.code)
        if not self.slug:
            base = slugify(f"{self.code}-{self.title}") or "course"
            self.slug = base[:220]
        super().save(*args, **kwargs)

    @property
    def default_section(self):
        return self.sections.filter(is_default=True).first()


class CourseAlias(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="aliases")
    alias = models.CharField(max_length=200)

    class Meta:
        unique_together = [("course", "alias")]

    def __str__(self) -> str:
        return self.alias

    def save(self, *args, **kwargs):
        self.alias = " ".join(self.alias.split()).upper()
        super().save(*args, **kwargs)


class Section(models.Model):
    """A course section. The default section is the course-wide room."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sections")
    professor = models.ForeignKey(
        "accounts.UserProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sections_taught",
    )
    term = models.CharField(max_length=40, blank=True, help_text="e.g. 'Fall 2026'.")
    section_code = models.CharField(max_length=40, blank=True, help_text="e.g. '002'.")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("course", "term", "section_code")]
        ordering = ["course__code", "term", "section_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["course"],
                condition=models.Q(is_default=True),
                name="one_default_section_per_course",
            )
        ]

    def __str__(self) -> str:
        if self.is_default:
            return f"{self.course.code} (course-wide)"
        label = f"{self.course.code} {self.section_code}".strip()
        return f"{label} — {self.professor}" if self.professor else label

    @property
    def display_name(self) -> str:
        if self.is_default:
            return f"{self.course.code} — All students"
        parts = [f"{self.course.code} {self.section_code}".strip()]
        if self.professor:
            parts.append(self.professor.public_name)
        if self.term:
            parts.append(self.term)
        return " · ".join(parts)


class Enrollment(models.Model):
    ROLE_STUDENT = "student"
    ROLE_TA = "ta"
    ROLE_PROFESSOR = "professor"
    ROLE_CHOICES = [
        (ROLE_STUDENT, "Student"),
        (ROLE_TA, "TA"),
        (ROLE_PROFESSOR, "Professor"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments"
    )
    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, related_name="enrollments"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    nickname = models.CharField(max_length=80, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "section")]
        ordering = ["section__course__code"]

    def __str__(self) -> str:
        return f"{self.user} in {self.section}"

    @property
    def course(self):
        return self.section.course
