from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import (
    BlockAttachment,
    BlockColumn,
    BlockType,
    CMSPage,
    MediaAsset,
    NavbarItem,
    PageBlock,
)


# ---------------------------------------------------------------------------
# Block types
# ---------------------------------------------------------------------------

class BlockTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockType
        fields = ["id", "name", "label", "description", "template_name", "config_schema"]


# ---------------------------------------------------------------------------
# Media
# ---------------------------------------------------------------------------

class MediaAssetSerializer(serializers.ModelSerializer):
    source_url = serializers.CharField(read_only=True)

    class Meta:
        model = MediaAsset
        fields = [
            "id", "title", "kind", "mime_type", "description",
            "source_url", "external_url", "file", "created_at",
        ]


class BlockAttachmentSerializer(serializers.ModelSerializer):
    media_asset_detail = MediaAssetSerializer(source="media_asset", read_only=True)

    class Meta:
        model = BlockAttachment
        fields = [
            "id", "media_asset", "media_asset_detail",
            "external_url", "embed_code", "caption",
            "display_order", "attachment_config",
        ]


# ---------------------------------------------------------------------------
# Columns
# ---------------------------------------------------------------------------

class BlockColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockColumn
        fields = [
            "id", "block", "width", "order",
            "horizontal_align", "vertical_align",
            "css_class", "background_color", "padding",
        ]


class BlockColumnWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockColumn
        fields = [
            "width", "order",
            "horizontal_align", "vertical_align",
            "css_class", "background_color", "padding",
        ]


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------

def _sanitize_html(value: str) -> str:
    import bleach
    ALLOWED_TAGS = [
        "a", "abbr", "b", "blockquote", "br", "code", "div", "em",
        "h1", "h2", "h3", "h4", "h5", "h6", "hr", "img", "li", "ol",
        "p", "pre", "section", "span", "strong", "table", "tbody",
        "td", "th", "thead", "tr", "ul",
    ]
    ALLOWED_ATTRS = {
        "*": ["class", "id", "style"],
        "a": ["href", "title", "target", "rel"],
        "img": ["src", "alt", "title", "width", "height"],
    }
    ALLOWED_PROTOCOLS = ["http", "https", "mailto"]
    return bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )


class PageBlockSerializer(serializers.ModelSerializer):
    block_type_detail = BlockTypeSerializer(source="block_type", read_only=True)
    attachments = BlockAttachmentSerializer(many=True, read_only=True)
    columns = BlockColumnSerializer(many=True, read_only=True)

    class Meta:
        model = PageBlock
        fields = [
            "id", "page", "block_type", "block_type_detail",
            "position", "span", "span_order",
            "config", "content", "parent_column",
            "attachments", "columns",
            "created_at", "updated_at",
        ]


class PageBlockWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageBlock
        fields = [
            "block_type", "position", "span", "span_order",
            "config", "content", "parent_column",
        ]

    def validate_content(self, value):
        return _sanitize_html(value) if value else value


# ---------------------------------------------------------------------------
# CMS Pages
# ---------------------------------------------------------------------------

class CMSPageListSerializer(serializers.ModelSerializer):
    preview_url = serializers.SerializerMethodField()

    class Meta:
        model = CMSPage
        fields = [
            "id", "title", "slug", "language", "layout", "columns",
            "show_title", "is_published", "is_public", "updated_at", "preview_url",
        ]

    @extend_schema_field(serializers.CharField())
    def get_preview_url(self, obj):
        return f"/{obj.language}/{obj.slug}/"


class CMSPageDetailSerializer(serializers.ModelSerializer):
    preview_url = serializers.SerializerMethodField()

    class Meta:
        model = CMSPage
        fields = [
            "id", "title", "slug", "content", "language", "layout", "columns",
            "show_title", "is_published", "published_at", "is_public",
            "created_at", "updated_at", "preview_url",
        ]
        read_only_fields = ["created_at", "updated_at", "published_at"]

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        slug = attrs.get("slug", instance.slug if instance else None)
        language = attrs.get("language", instance.language if instance else None)
        qs = CMSPage.objects.filter(slug=slug, language=language)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {"slug": "A page with this slug already exists in this language."}
            )
        return attrs

    @extend_schema_field(serializers.CharField())
    def get_preview_url(self, obj):
        return f"/{obj.language}/{obj.slug}/"


# ---------------------------------------------------------------------------
# Navbar
# ---------------------------------------------------------------------------

class NavbarItemSerializer(serializers.ModelSerializer):
    cms_page_title = serializers.CharField(source="cms_page.title", read_only=True)

    class Meta:
        model = NavbarItem
        fields = [
            "id", "title", "language", "cms_page", "cms_page_title",
            "external_url", "sort_order", "parent", "is_public", "level",
        ]