from django.urls import path

from .api import (
    AttachmentDetailApi,
    BlockAttachmentsApi,
    BlockDetailApi,
    BlockTypesApi,
    CMSPageDetailApi,
    CMSPageListCreateApi,
    CMSPagePublishApi,
    ColumnDetailApi,
    DuplicateBlockApi,
    MediaAssetsApi,
    NavbarItemDetailApi,
    NavbarItemsApi,
    PageBlocksApi,
    ReorderBlocksApi,
    SessionInfoApi,
)
from .version_api_views import PageVersionRestoreApi, PageVersionsApi
from .public_views import CMSHomeView, CMSPageListView, CMSPageView, NavbarView
from .public_api import PublicNavbarApi, PublicPageDetailApi, PublicPageListApi

app_name = "basecms"

urlpatterns = [

    # ── Public site — React shell ─────────────────────────────────────────────
    # Each URL serves react_site.html; the React SPA fetches its own data.
    path("", CMSHomeView.as_view(), name="home"),
    path("navbar/", NavbarView.as_view(), name="navbar"),
    path("<str:lang>/pages/", CMSPageListView.as_view(), name="cms_page_list"),
    path("<str:lang>/<slug:slug>/", CMSPageView.as_view(), name="cms_page_preview"),

    # ── Public JSON API (no auth required) ───────────────────────────────────
    path("api/public/pages/", PublicPageListApi.as_view(), name="public_page_list"),
    path("api/public/navbar/", PublicNavbarApi.as_view(), name="public_navbar"),
    path("<str:lang>/<slug:slug>/data/", PublicPageDetailApi.as_view(), name="public_page_data"),

    # ── Cockpit auth ──────────────────────────────────────────────────────────
    path("api/cockpit/auth/me/", SessionInfoApi.as_view(), name="session-info"),

    # ── Cockpit pages ─────────────────────────────────────────────────────────
    path("api/cockpit/cms/pages/", CMSPageListCreateApi.as_view(), name="cockpit_cms_pages"),
    path("api/cockpit/cms/pages/<int:pk>/", CMSPageDetailApi.as_view(), name="cockpit_cms_page_detail"),
    path("api/cockpit/cms/pages/<int:pk>/publish/", CMSPagePublishApi.as_view(), name="cockpit_cms_page_publish"),

    # ── Cockpit blocks ────────────────────────────────────────────────────────
    path("api/cockpit/cms/block-types/", BlockTypesApi.as_view(), name="cockpit_block_types"),
    path("api/cockpit/cms/pages/<int:page_id>/blocks/", PageBlocksApi.as_view(), name="cockpit_page_blocks"),
    path("api/cockpit/cms/blocks/<int:pk>/", BlockDetailApi.as_view(), name="cockpit_block_detail"),
    path("api/cockpit/cms/blocks/<int:pk>/duplicate/", DuplicateBlockApi.as_view(), name="cockpit_block_duplicate"),
    path("api/cockpit/cms/pages/<int:page_id>/reorder-blocks/", ReorderBlocksApi.as_view(), name="cockpit_reorder_blocks"),
    path("api/cockpit/cms/columns/<int:pk>/", ColumnDetailApi.as_view(), name="cockpit_column_detail"),

    # ── Cockpit media ─────────────────────────────────────────────────────────
    path("api/cockpit/cms/media-assets/", MediaAssetsApi.as_view(), name="cockpit_media_assets"),
    path("api/cockpit/cms/blocks/<int:block_id>/attachments/", BlockAttachmentsApi.as_view(), name="cockpit_block_attachments"),
    path("api/cockpit/cms/attachments/<int:pk>/", AttachmentDetailApi.as_view(), name="cockpit_attachment_detail"),

    # ── Cockpit navbar ────────────────────────────────────────────────────────
    path("api/cockpit/cms/navbar-items/", NavbarItemsApi.as_view(), name="cockpit_navbar_items"),
    path("api/cockpit/cms/navbar-items/<int:pk>/", NavbarItemDetailApi.as_view(), name="cockpit_navbar_item_detail"),

    # ── Cockpit versions ──────────────────────────────────────────────────────
    path("api/cockpit/cms/pages/<int:page_id>/versions/", PageVersionsApi.as_view(), name="cockpit_page_versions"),
    path("api/cockpit/cms/pages/<int:page_id>/versions/<int:version_id>/restore/", PageVersionRestoreApi.as_view(), name="cockpit_page_version_restore"),
]
