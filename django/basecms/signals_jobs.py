"""
Job-dispatch signals. Only loaded when django_q is installed (see apps.py).
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CMSPage, MediaAsset
from .job_services import queue_media_processing, queue_page_reindex


@receiver(post_save, sender=MediaAsset)
def process_media_after_create(sender, instance: MediaAsset, created: bool, **kwargs):
    if created:
        queue_media_processing(instance.pk)


@receiver(post_save, sender=CMSPage)
def reindex_page_after_save(sender, instance: CMSPage, created: bool, **kwargs):
    queue_page_reindex(instance.pk)
