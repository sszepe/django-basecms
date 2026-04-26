from drf_spectacular.utils import OpenApiExample

PAGE_CREATE_EXAMPLE = OpenApiExample(
    "Create page",
    value={
        "title": "About Open Data",
        "slug": "about-open-data",
        "content": "<p>Intro text</p>",
        "language": "en",
        "layout": "vertical",
        "columns": 1,
        "show_title": True,
        "is_published": False,
        "is_public": True,
    },
    request_only=True,
)

PAGE_RESPONSE_EXAMPLE = OpenApiExample(
    "Page response",
    value={
        "id": 12,
        "title": "About Open Data",
        "slug": "about-open-data",
        "content": "<p>Intro text</p>",
        "language": "en",
        "layout": "vertical",
        "columns": 1,
        "show_title": True,
        "is_published": False,
        "published_at": None,
        "is_public": True,
        "created_at": "2026-04-21T11:30:00Z",
        "updated_at": "2026-04-21T11:30:00Z",
        "preview_url": "/en/about-open-data",
    },
    response_only=True,
)

HTML_BLOCK_CREATE_EXAMPLE = OpenApiExample(
    "Create HTML block",
    value={
        "block_type": 1,
        "position": 0,
        "span": 12,
        "span_order": 0,
        "config": {
            "editor_mode": "visual"
        },
        "content": "<section><h2>Open Data</h2><p>Welcome.</p></section>",
        "parent_column": None,
    },
    request_only=True,
)

HTML_BLOCK_CONFIG_EXAMPLE = OpenApiExample(
    "HTML block config",
    value={
        "editor_mode": "html"
    },
)

MEDIA_EMBED_BLOCK_CONFIG_EXAMPLE = OpenApiExample(
    "Media embed block config",
    value={
        "alignment": "center",
        "size": "medium",
        "autoplay": False,
        "controls": True,
        "loop": False,
        "muted": False,
    },
)

COLUMN_BLOCK_CREATE_EXAMPLE = OpenApiExample(
    "Create column block",
    value={
        "block_type": 5,
        "position": 1,
        "span": 12,
        "span_order": 0,
        "config": {
            "gap": "3",
            "stack_on_mobile": True
        },
        "content": "",
        "parent_column": None,
    },
    request_only=True,
)

REORDER_BLOCKS_EXAMPLE = OpenApiExample(
    "Reorder blocks",
    value={
        "blocks": [
            {"id": 21, "position": 0, "span_order": 0, "span": 12, "parent_column": None},
            {"id": 22, "position": 1, "span_order": 0, "span": 12, "parent_column": None},
            {"id": 24, "position": 1, "span_order": 0, "span": 6, "parent_column": 3},
        ]
    },
    request_only=True,
)

MEDIA_UPLOAD_MULTIPART_EXAMPLE = OpenApiExample(
    "Create media asset",
    summary="Multipart upload example",
    description="Send as multipart/form-data with a file field when uploading local media.",
    value={
        "title": "Repository teaser image",
        "kind": "image",
        "file": "<binary file>",
        "description": "Homepage teaser",
    },
    request_only=True,
)

MEDIA_EXTERNAL_EXAMPLE = OpenApiExample(
    "Create external media asset",
    value={
        "title": "External PDF",
        "kind": "document",
        "external_url": "https://example.org/open-data.pdf",
        "description": "Linked external document",
    },
    request_only=True,
)

ATTACH_MEDIA_ASSET_EXAMPLE = OpenApiExample(
    "Attach media asset",
    value={
        "media_asset": 7,
        "caption": "Cover image",
        "display_order": 0,
        "attachment_config": {},
    },
    request_only=True,
)

ATTACH_EXTERNAL_URL_EXAMPLE = OpenApiExample(
    "Attach external URL",
    value={
        "external_url": "https://example.org/stream.mp4",
        "caption": "External stream",
        "display_order": 0,
        "attachment_config": {},
    },
    request_only=True,
)

ATTACH_EMBED_EXAMPLE = OpenApiExample(
    "Attach embed code",
    value={
        "embed_code": "<iframe src='https://player.example.org/embed/123'></iframe>",
        "caption": "Embedded player",
        "display_order": 0,
        "attachment_config": {},
    },
    request_only=True,
)

NAVBAR_CREATE_EXAMPLE = OpenApiExample(
    "Create navbar item",
    value={
        "title": "Open Data",
        "language": "en",
        "cms_page": 12,
        "external_url": None,
        "sort_order": 0,
        "parent": None,
        "is_public": True,
    },
    request_only=True,
)

VERSION_SNAPSHOT_EXAMPLE = OpenApiExample(
    "Create version snapshot",
    value={
        "change_summary": "Prepared revised homepage intro and hero media"
    },
    request_only=True,
)

VERSION_RESTORE_EXAMPLE = OpenApiExample(
    "Restore version",
    value={
        "confirm": True
    },
    request_only=True,
)
