"""
public_views.py — views for public-facing CMS pages.

The rendering mode is controlled by settings.SERVE_PUBLIC_PAGES:

  "django"   → CMSPageView renders basecms/page.html using Django templates
               and the {% render_block %} template tag. All HTML is produced
               server-side; no React or Vite build is required at runtime.

  "frontend" → CMSPageView serves basecms/react_site.html — a thin shell that
               injects window.__SITE_CONFIG__ and loads the Vite-built React
               SPA. The SPA fetches page data from /<lang>/<slug>/data/ and
               renders blocks client-side.

Both modes share the same access-control logic (404/403 on missing or
restricted pages) and the same CMSPageListView / NavbarView helpers.
"""
import json
from functools import lru_cache

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import DetailView, TemplateView

from .models import CMSPage, NavbarItem, PageBlock
from .views import build_nav_tree


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _language_codes() -> tuple[str, ...]:
    """Cached tuple of configured language codes, e.g. ('en', 'de')."""
    return tuple(code for code, _name in settings.AVAILABLE_LANGUAGES)


def _default_language() -> str:
    codes = _language_codes()
    return codes[0] if codes else "en"


def _is_frontend_mode() -> bool:
    return getattr(settings, "SERVE_PUBLIC_PAGES", "django") == "frontend"


def _site_config_context(current_language: str) -> dict:
    """Template context vars consumed by react_site.html."""
    codes = list(_language_codes())
    return {
        "available_language_codes_json": json.dumps(codes),
        "default_language": codes[0] if codes else "en",
        "current_language": current_language,
    }


# ---------------------------------------------------------------------------
# Public page view — branches on SERVE_PUBLIC_PAGES
# ---------------------------------------------------------------------------

class CMSPageView(View):
    """
    Dispatches to either the Django-template renderer or the React shell
    depending on settings.SERVE_PUBLIC_PAGES.

    A single class is used so urls.py stays unconditional — the decision
    is made at request time, which means you can change the setting and
    reload without touching URL config.
    """

    def get(self, request, lang: str, slug: str):
        if _is_frontend_mode():
            return _FrontendPageView.as_view()(request, lang=lang, slug=slug)
        return _DjangoPageView.as_view()(request, lang=lang, slug=slug)


class CMSHomeView(View):
    """Maps / to the default language's index page."""

    def get(self, request):
        lang = _default_language()
        return CMSPageView.as_view()(request, lang=lang, slug="index")


# ---------------------------------------------------------------------------
# "django" mode — server-side Django template rendering
# ---------------------------------------------------------------------------

class _DjangoPageView(DetailView):
    """
    Renders a published CMS page using Django templates.

    Template: basecms/page.html
    Blocks are rendered via {% render_block block %} (cms_tags.py).
    """
    model = CMSPage
    template_name = "basecms/page.html"
    context_object_name = "page"

    def get_queryset(self):
        user = self.request.user
        return (
            CMSPage.get_visible_pages_for_user(
                user,
                language=self.kwargs["lang"],
                published_only=True,
            )
            .prefetch_related(
                Prefetch(
                    "blocks",
                    queryset=(
                        PageBlock.objects
                        # FIX: also select_related parent_column so that
                        # parent_column_id is available without extra queries
                        # (used by the top_level_blocks filter and _render_column).
                        .select_related("block_type", "parent_column")
                        .prefetch_related(
                            "attachments__media_asset",
                            "columns",
                            # FIX: prefetch nested blocks' block_type and
                            # attachments so _render_column doesn't hit the DB
                            # again for each column block's children.
                            "columns__nested_blocks__block_type",
                            "columns__nested_blocks__attachments__media_asset",
                            "columns__nested_blocks__columns",
                        )
                        .order_by("position", "span_order")
                    ),
                )
            )
        )

    def get_object(self):
        page = get_object_or_404(
            self.get_queryset(),
            slug=self.kwargs["slug"],
            language=self.kwargs["lang"],
        )
        if not page.user_can_view(self.request.user):
            raise PermissionDenied
        return page

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # FIX: use list() so Django returns the already-evaluated prefetch cache
        # instead of issuing a fresh queryset that bypasses select_related/prefetch.
        context["blocks"] = list(self.object.blocks.all())
        context["current_language"] = self.kwargs["lang"]
        return context


# ---------------------------------------------------------------------------
# "frontend" mode — React SPA shell
# ---------------------------------------------------------------------------

class _FrontendPageView(TemplateView):
    """
    Serves the React SPA shell (react_site.html).

    Validates page access (404/403) before responding so the shell is never
    sent for non-existent or restricted pages.  Fetches minimal page metadata
    for the <title> tag; full page data is loaded by the SPA after mount.
    """
    template_name = "basecms/react_site.html"

    def _validate_access(self):
        lang = self.kwargs["lang"]
        slug = self.kwargs["slug"]
        qs = CMSPage.get_visible_pages_for_user(
            self.request.user, language=lang, published_only=True
        )
        page = get_object_or_404(qs, slug=slug, language=lang)
        if not page.user_can_view(self.request.user):
            raise PermissionDenied
        return page

    def get(self, request, *args, **kwargs):
        self._validate_access()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lang = self.kwargs.get("lang", _default_language())
        slug = self.kwargs.get("slug", "index")

        try:
            page = CMSPage.objects.only("title", "content").get(slug=slug, language=lang)
            context["page_title"] = page.title
            context["page_description"] = (page.content or "")[:160].strip()
        except CMSPage.DoesNotExist:
            context["page_title"] = "basecms"
            context["page_description"] = ""

        context.update(_site_config_context(lang))
        return context


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class CMSPageListView(View):
    """JSON list of published pages (used by cockpit page picker)."""

    def get(self, request, *args, **kwargs):
        language = request.GET.get("language") or kwargs.get("lang")
        if not language:
            return JsonResponse({"pages": []})
        pages = (
            CMSPage.get_visible_pages_for_user(
                request.user, language=language, published_only=True
            )
            .order_by("title")
        )
        return JsonResponse({
            "pages": [
                {"id": p.id, "title": p.title, "slug": p.slug, "language": p.language}
                for p in pages
            ]
        })


class NavbarView(View):
    """JSON navbar tree (used by the public React site and cockpit)."""

    def get(self, request, *args, **kwargs):
        language = request.GET.get("language") or kwargs.get("lang", _default_language())
        qs = NavbarItem.get_visible_items_for_user(request.user, language=language)
        tree = build_nav_tree(qs, request.user)

        def _node(item):
            return {
                "id": item.id,
                "title": item.title,
                "sort_order": item.sort_order,
                "is_public": item.is_public,
                "level": item.nav_level,
                "cms_page": {
                    "id": item.cms_page.id,
                    "slug": item.cms_page.slug,
                    "title": item.cms_page.title,
                } if item.cms_page else None,
                "external_url": item.external_url or "",
                "children": [_node(c) for c in item.visible_children],
            }

        return JsonResponse({"language": language, "items": [_node(n) for n in tree]})
