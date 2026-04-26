from django.contrib import admin
from django.utils.html import format_html
from guardian.admin import GuardedModelAdmin

from .forms import NavbarItemAdminForm, CMSPageAdminForm
from .models import (
    CMSPage,
    NavbarItem,
    BlockType,
    PageBlock,
    PageVersion,
    BlockTemplate,
    BlockColumn,
    ColumnBlockConfig,
    MediaAsset,
    BlockAttachment,
)


@admin.register(CMSPage)
class CMSPageAdmin(GuardedModelAdmin):
    form = CMSPageAdminForm
    list_display = (
        "title", "language", "slug", "layout", "columns",
        "is_public", "is_published", "block_count",
        "preview_link", "cockpit_link", "updated_at",
    )
    list_filter = ("language", "layout", "is_published", "is_public", "show_title")
    search_fields = ("title", "slug", "content")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at", "published_at", "created_by", "preview_link", "cockpit_link")
    fieldsets = (
        ("Content", {"fields": ("title", "slug", "language", "content", "show_title")}),
        ("Layout", {"fields": ("layout", "columns")}),
        ("Visibility", {"fields": ("is_public", "is_published", "published_at")}),
        ("Links", {"fields": ("preview_link", "cockpit_link")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_at")}),
    )

    def block_count(self, obj):
        return obj._block_count
    block_count.short_description = "Blocks"
    block_count.admin_order_field = "_block_count"

    def preview_link(self, obj):
        return format_html('<a href="/{}/{}" target="_blank">Open public page</a>', obj.language, obj.slug)
    preview_link.short_description = "Preview"

    def cockpit_link(self, obj):
        return format_html('<a href="/cockpit/cms-pages/{}" target="_blank">Open in cockpit</a>', obj.pk)
    cockpit_link.short_description = "Cockpit"

    def get_queryset(self, request):
        from django.db.models import Count
        return (
            super().get_queryset(request)
            .annotate(_block_count=Count("blocks"))
        )


@admin.register(NavbarItem)
class NavbarItemAdmin(GuardedModelAdmin):
    form = NavbarItemAdminForm
    list_display = (
        "title_with_indent", "language", "parent", "sort_order",
        "target_display", "is_public", "level_display", "cockpit_link",
    )
    list_editable = ("sort_order", "is_public")
    list_filter = ("language", "is_public")
    search_fields = ("title", "external_url", "cms_page__title", "cms_page__slug")
    ordering = ("language", "parent_id", "sort_order", "title")
    readonly_fields = ("level_display", "cockpit_link")
    fieldsets = (
        ("Basic Information", {"fields": ("title", "language", "parent", "sort_order")}),
        ("Target", {"fields": ("cms_page", "external_url")}),
        ("Visibility", {"fields": ("is_public",)}),
        ("Info", {"fields": ("level_display", "cockpit_link")}),
    )

    def get_queryset(self, request):
        # select_related parent chain so level property doesn't cause N+1 queries
        return (
            super().get_queryset(request)
            .select_related("parent", "parent__parent", "parent__parent__parent", "cms_page")
        )

    def title_with_indent(self, obj):
        return format_html("{}{}", format_html("&nbsp;" * (obj.level * 4)), obj.title)
    title_with_indent.short_description = "Title"

    def level_display(self, obj):
        return obj.level
    level_display.short_description = "Level"

    def target_display(self, obj):
        if obj.cms_page:
            return f"Page: {obj.cms_page.title}"
        if obj.external_url:
            return obj.external_url
        return "—"
    target_display.short_description = "Target"

    def cockpit_link(self, obj):
        return format_html('<a href="/cockpit/cms-navbar" target="_blank">Open navbar editor</a>')
    cockpit_link.short_description = "Cockpit"


@admin.register(BlockType)
class BlockTypeAdmin(admin.ModelAdmin):
    list_display = ("label", "name", "template_name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "label", "description")
    readonly_fields = ("name",)


class BlockAttachmentInline(admin.TabularInline):
    model = BlockAttachment
    extra = 0
    fields = ("media_asset", "external_url", "embed_code", "caption", "display_order")
    autocomplete_fields = ("media_asset",)


class BlockColumnInline(admin.TabularInline):
    model = BlockColumn
    extra = 0
    fields = ("order", "width", "horizontal_align", "vertical_align", "padding")


@admin.register(PageBlock)
class PageBlockAdmin(admin.ModelAdmin):
    list_display = (
        "__str__", "page", "block_type", "position",
        "span", "span_order", "parent_column", "preview_page_link", "updated_at",
    )
    list_filter = ("block_type", "page__language", "parent_column")
    search_fields = ("page__title", "content")
    autocomplete_fields = ["page", "parent_column"]
    readonly_fields = ("created_at", "updated_at", "preview_page_link")
    inlines = [BlockAttachmentInline, BlockColumnInline]
    fieldsets = (
        ("Placement", {"fields": ("page", "block_type", "position", "span", "span_order", "parent_column")}),
        ("Content", {"fields": ("content", "config")}),
        ("Links", {"fields": ("preview_page_link",)}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("page", "block_type", "parent_column")

    def preview_page_link(self, obj):
        return format_html('<a href="/{}/{}" target="_blank">Open page</a>', obj.page.language, obj.page.slug)
    preview_page_link.short_description = "Public page"


@admin.register(PageVersion)
class PageVersionAdmin(admin.ModelAdmin):
    list_display = ("page", "version_number", "title", "created_at", "created_by", "restore_hint")
    list_filter = ("page__language", "created_at")
    search_fields = ("page__title", "title", "change_summary")
    readonly_fields = ("page", "version_number", "title", "content_snapshot", "created_at", "created_by", "change_summary")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("page", "created_by")

    def restore_hint(self, obj):
        return format_html(
            'Restore from cockpit: <a href="/cockpit/cms-pages/{}" target="_blank">Open page</a>',
            obj.page_id,
        )
    restore_hint.short_description = "Restore"


@admin.register(BlockTemplate)
class BlockTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "block_type", "is_public", "created_by")
    list_filter = ("block_type", "is_public")
    search_fields = ("name", "description")


@admin.register(BlockColumn)
class BlockColumnAdmin(admin.ModelAdmin):
    list_display = ("id", "block", "order", "width", "horizontal_align", "vertical_align", "padding")
    list_filter = ("horizontal_align", "vertical_align")
    search_fields = ("block__page__title",)   # required by PageBlockAdmin.autocomplete_fields
    autocomplete_fields = ("block",)


@admin.register(ColumnBlockConfig)
class ColumnBlockConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "block", "gap", "row_horizontal_align", "stack_on_mobile")
    list_filter = ("gap", "row_horizontal_align", "stack_on_mobile")
    autocomplete_fields = ("block",)


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "mime_type", "created_at", "file_link", "cockpit_hint")
    list_filter = ("kind",)
    search_fields = ("title", "description", "source_url", "external_url")
    readonly_fields = ("created_at", "file_link", "cockpit_hint")

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">Open file</a>', obj.file.url)
        if obj.external_url:
            return format_html('<a href="{}" target="_blank">Open external URL</a>', obj.external_url)
        return "—"
    file_link.short_description = "Asset"

    def cockpit_hint(self, obj):
        return "Attach and manage assets through the cockpit media picker."
    cockpit_hint.short_description = "Usage"
