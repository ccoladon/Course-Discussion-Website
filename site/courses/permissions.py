"""Shared permission helpers for course-scoped access."""

from __future__ import annotations

from courses.models import Enrollment


def is_enrolled_in_course(user, course_id: int) -> bool:
    return Enrollment.objects.filter(user=user, section__course_id=course_id).exists()


def enrollment_for_section(user, section_id: int):
    return (
        Enrollment.objects.filter(user=user, section_id=section_id)
        .select_related("section__course")
        .first()
    )


def can_moderate_section(user, section) -> bool:
    if user.is_staff or user.is_superuser:
        return True
    if section.professor_id and section.professor.user_id == user.id:
        return True
    return Enrollment.objects.filter(
        user=user, section=section, role__in=[Enrollment.ROLE_PROFESSOR, Enrollment.ROLE_TA]
    ).exists()
