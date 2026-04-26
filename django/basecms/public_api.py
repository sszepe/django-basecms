"""
Public read-only JSON API — no authentication required.

Endpoints:
  GET /api/public/pages/?language=en        — list published pages
  GET /api/public/navbar/?language=en       — navbar tree
  GET /<lang>/<slug>/data/                  — full page + blocks JSON
"""
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from drf_spectacular.types import OpenApiTypes

from .models import CMSPage, NavbarItem, PageBlock
from .views import build_nav_tree


# ── Inline schema helpers ─────────────────────────────────────────────────────
# These lightweight serializers exist only for OpenAPI documentation.
# The actual responses are built manually and returned as JsonResponse.

class _MediaAssetSchema(serializers.Serializer):
    id           = serializers.IntegerField()
    title        = serializers.CharField()
    kind         = serializers.CharField()
    mime_type    = serializers.CharField()
    source_url   = serializers.CharField()
    external_url = serializers.CharField()
    file_url     = serializers.CharField()

class _AttachmentSchema(serializers.Serializer):
    id                = serializers.IntegerField()
    display_order     = serializers.IntegerField()
    caption           = serializers.CharField()
    embed_code        = serializers.CharField()
    external_url      = serializers.CharField()
    attachment_config = serializers.DictField()
    media_asset       = _MediaAssetSchema(allow_null=True)

class _ColumnSchema(serializers.Serializer):
    id               = serializers.IntegerField()
    order            = serializers.IntegerField()
    width            = serializers.IntegerField()
    horizontal_align = serializers.CharField()
    vertical_align   = serializers.CharField()
    css_class        = serializers.CharField()
    background_color = serializers.CharField()
    padding          = serializers.CharField()

class _BlockTypeSchema(serializers.Serializer):
    id    = serializers.IntegerField()
    name  = serializers.CharField()
    label = serializers.CharField()

class _BlockSchema(serializers.Serializer):
    id            = serializers.IntegerField()
    position      = serializers.IntegerField()
    span          = serializers.IntegerField()
    span_order    = serializers.IntegerField()
    parent_column = serializers.IntegerField(allow_null=True)
    block_type    = _BlockTypeSchema()
    config        = serializers.DictField()
    content       = serializers.CharField()
    attachments   = _AttachmentSchema(many=True)
    columns       = _ColumnSchema(many=True)

class _PageSchema(serializers.Serializer):
    id           = serializers.IntegerField()
    title        = serializers.CharField()
    slug         = serializers.CharField()
    language     = serializers.CharField()
    layout       = serializers.CharField()
    columns      = serializers.IntegerField()
    show_title   = serializers.BooleanField()
    is_public    = serializers.BooleanField()
    published_at = serializers.CharField(allow_null=True)

class _PageListResponseSchema(serializers.Serializer):
    pages = _PageSchema(many=True)

class _PageDetailResponseSchema(serializers.Serializer):
    page   = _PageSchema()
    blocks = _BlockSchema(many=True)

class _NavbarNodeSchema(serializers.Serializer):
    id         = serializers.IntegerField()
    title      = serializers.CharField()
    sort_order = serializers.IntegerField()
    is_public  = serializers.BooleanField()
    level      = serializers.IntegerField()
    cms_page   = serializers.DictField(allow_null=True)
    external_url = serializers.CharField()
    children   = serializers.ListField()   # recursive — simplified for schema

class _NavbarResponseSchema(serializers.Serializer):
    language = serializers.CharField()
    items    = _NavbarNodeSchema(many=True)


# ── Serialisation helpers ─────────────────────────────────────────────────────

def _attachment_data(att) -> dict:
    asset = att.media_asset
    return {
        "id": att.id,
        "display_order": att.display_order,
        "caption": att.caption or "",
        "embed_code": att.embed_code or "",
        "external_url": att.external_url or "",
        "attachment_config": att.attachment_config or {},
        "media_asset": {
            "id": asset.id,
            "title": asset.title,
            "kind": asset.kind,
            "mime_type": asset.mime_type or "",
            "source_url": asset.source_url or "",
            "external_url": asset.external_url or "",
            "file_url": asset.file.url if asset.file else "",
        } if asset else None,
    }


def _column_data(col) -> dict:
    return {
        "id": col.id,
        "order": col.order,
        "width": col.width,
        "horizontal_align": col.horizontal_align,
        "vertical_align": col.vertical_align,
        "css_class": col.css_class or "",
        "background_color": col.background_color or "",
        "padding": col.padding or "3",
    }


def _block_data(block) -> dict:
    return {
        "id": block.id,
        "position": block.position,
        "span": block.span,
        "span_order": block.span_order,
        "parent_column": block.parent_column_id,
        "block_type": {
            "id": block.block_type.id,
            "name": block.block_type.name,
            "label": block.block_type.label,
        },
        "config": block.config or {},
        "content": block.content or "",
        "attachments": [_attachment_data(a) for a in block.attachments.all()],
        "columns": [_column_data(c) for c in block.columns.all()],
    }


def _page_data(page) -> dict:
    return {
        "id": page.id,
        "title": page.title,
        "slug": page.slug,
        "language": page.language,
        "layout": page.layout,
        "columns": page.columns,
        "show_title": page.show_title,
        "is_public": page.is_public,
        "published_at": page.published_at.isoformat() if page.published_at else None,
    }


def _navbar_node(item) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "sort_order": item.sort_order,
        "is_public": item.is_public,
        "level": item.level,
        "cms_page": {
            "id": item.cms_page.id,
            "slug": item.cms_page.slug,
            "title": item.cms_page.title,
        } if item.cms_page else None,
        "external_url": item.external_url or "",
        "children": [_navbar_node(c) for c in getattr(item, "visible_children", [])],
    }


# ── Views ─────────────────────────────────────────────────────────────────────

class PublicPageListApi(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = None

    @extend_schema(
        tags=["Public"],
        summary="List published pages",
        parameters=[OpenApiParameter("language", str, OpenApiParameter.QUERY, required=False)],
        responses={200: _PageListResponseSchema},
    )
    def get(self, request):
        language = request.GET.get("language", "")
        qs = CMSPage.get_visible_pages_for_user(request.user, published_only=True)
        if language:
            qs = qs.filter(language=language)
        return JsonResponse({"pages": [_page_data(p) for p in qs.order_by("language", "title")]})


class PublicNavbarApi(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = None

    @extend_schema(
        tags=["Public"],
        summary="Navbar tree",
        parameters=[OpenApiParameter("language", str, OpenApiParameter.QUERY, required=False)],
        responses={200: _NavbarResponseSchema},
    )
    def get(self, request):
        language = request.GET.get("language", "en")
        qs = NavbarItem.get_visible_items_for_user(request.user, language=language)
        tree = build_nav_tree(qs, request.user)
        return JsonResponse({"language": language, "items": [_navbar_node(n) for n in tree]})


class PublicPageDetailApi(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = None

    @extend_schema(
        tags=["Public"],
        summary="Page detail with blocks",
        responses={200: _PageDetailResponseSchema},
    )
    def get(self, request, lang: str, slug: str):
        page_qs = (
            CMSPage.get_visible_pages_for_user(request.user, language=lang, published_only=True)
            .prefetch_related(
                Prefetch(
                    "blocks",
                    queryset=PageBlock.objects
                    .select_related("block_type", "parent_column")
                    .prefetch_related("attachments__media_asset", "columns")
                    .order_by("position", "span_order"),
                )
            )
        )
        page = get_object_or_404(page_qs, slug=slug, language=lang)
        return JsonResponse({
            "page": _page_data(page),
            "blocks": [_block_data(b) for b in page.blocks.all()],
        })