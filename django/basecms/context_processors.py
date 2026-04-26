
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import get_language
from .models import NavbarItem, CMSPage, NavbarCacheVersion
from .views import build_nav_tree


def navbar_context(request):
    path_parts = request.path.strip("/").split("/")
    user = request.user

    available_language_codes = [code[:2] for code, _ in settings.AVAILABLE_LANGUAGES]
    path_lang = path_parts[0] if path_parts and path_parts[0] in available_language_codes else None
    current_language = path_lang or get_language()[:2]

    visible_pages = CMSPage.get_visible_pages_for_user(
        user,
        language=current_language,
        published_only=True,
    )
    if not visible_pages.exists():
        current_language = get_language()[:2]

    cache_version = NavbarCacheVersion.get_version(current_language)
    if user.is_anonymous:
        cache_key = f"navbar_items_anonymous_{current_language}_v{cache_version}"
    elif user.is_superuser:
        cache_key = f"navbar_items_superuser_{current_language}_v{cache_version}"
    else:
        cache_key = f"navbar_items_user_{user.pk}_{current_language}_v{cache_version}"

    navbar_items = cache.get(cache_key)
    if navbar_items is None:
        base_queryset = (
            NavbarItem.objects.filter(language=current_language)
            .select_related("cms_page", "parent")
        )

        if user.is_anonymous:
            items_qs = base_queryset.filter(is_public=True)
        elif user.is_superuser:
            items_qs = base_queryset
        else:
            from guardian.shortcuts import get_objects_for_user

            permitted_items = get_objects_for_user(
                user,
                "basecms.view_navbaritem",
                klass=base_queryset,
                accept_global_perms=False,
            )
            public_items = base_queryset.filter(is_public=True)
            items_qs = (public_items | permitted_items).distinct()

        accessible_ids = []
        for item in items_qs:
            if item.cms_page:
                if item.cms_page.user_can_view(user):
                    accessible_ids.append(item.pk)
            else:
                accessible_ids.append(item.pk)

        visible_qs = base_queryset.filter(pk__in=accessible_ids)
        navbar_items = build_nav_tree(visible_qs, user)
        cache.set(cache_key, navbar_items, 60 * 15)

    available_languages = [
        (code[:2], name)
        for code, name in settings.AVAILABLE_LANGUAGES
        if code[:2] != current_language
    ]

    if len(path_parts) >= 3 and path_parts[1] == "pages":
        current_slug = path_parts[2]
    elif len(path_parts) >= 2:
        current_slug = path_parts[1]
    else:
        current_slug = "index"

    return {
        "primary_path": path_parts[0] if path_parts else "no_path",
        "navbar_items": navbar_items,
        "current_language": current_language,
        "available_languages": available_languages,
        "current_slug": current_slug,
        "show_cms_link": bool(user.is_authenticated and user.is_staff),
        "cms_link": "/cockpit/cms-pages",
    }
