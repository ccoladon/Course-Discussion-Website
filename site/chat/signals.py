from django.db.models.signals import post_save
from django.dispatch import receiver

from courses.models import Section

from .models import Channel


@receiver(post_save, sender=Section)
def create_default_channels(sender, instance, created, **kwargs):
    if not created:
        return
    for kind in Channel.DEFAULT_CHANNELS:
        Channel.objects.get_or_create(section=instance, name=kind, defaults={"kind": kind})
