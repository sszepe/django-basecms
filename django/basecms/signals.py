from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from guardian.models import GroupObjectPermission, UserObjectPermission
from .models import CMSPage, NavbarCacheVersion, NavbarItem

@receiver([post_save, post_delete], sender=NavbarItem)
def invalidate_navbar_cache(sender, instance, **kwargs):
    NavbarCacheVersion.increment_version(instance.language)

@receiver([post_save, post_delete], sender=CMSPage)
def invalidate_page_cache(sender, instance, **kwargs):
    NavbarCacheVersion.increment_version(instance.language)

@receiver([post_save, post_delete], sender=UserObjectPermission)
def invalidate_user_perm_cache(sender, instance, **kwargs):
    navbar_ct = ContentType.objects.get_for_model(NavbarItem)
    page_ct = ContentType.objects.get_for_model(CMSPage)
    if instance.content_type == navbar_ct and instance.permission.codename == "view_navbaritem":
        try:
            item = NavbarItem.objects.get(pk=instance.object_pk)
            NavbarCacheVersion.increment_version(item.language)
        except NavbarItem.DoesNotExist:
            pass
    if instance.content_type == page_ct and instance.permission.codename == "view_cmspage":
        try:
            page = CMSPage.objects.get(pk=instance.object_pk)
            NavbarCacheVersion.increment_version(page.language)
        except CMSPage.DoesNotExist:
            pass

@receiver([post_save, post_delete], sender=GroupObjectPermission)
def invalidate_group_perm_cache(sender, instance, **kwargs):
    navbar_ct = ContentType.objects.get_for_model(NavbarItem)
    page_ct = ContentType.objects.get_for_model(CMSPage)
    if instance.content_type == navbar_ct and instance.permission.codename == "view_navbaritem":
        try:
            item = NavbarItem.objects.get(pk=instance.object_pk)
            NavbarCacheVersion.increment_version(item.language)
        except NavbarItem.DoesNotExist:
            pass
    if instance.content_type == page_ct and instance.permission.codename == "view_cmspage":
        try:
            page = CMSPage.objects.get(pk=instance.object_pk)
            NavbarCacheVersion.increment_version(page.language)
        except CMSPage.DoesNotExist:
            pass
