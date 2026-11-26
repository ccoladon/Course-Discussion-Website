from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Course, Section


@receiver(post_save, sender=Course)
def create_default_section(sender, instance, created, **kwargs):
    if not created:
        return
    Section.objects.get_or_create(
        course=instance,
        is_default=True,
        defaults={"term": "", "section_code": ""},
    )
