from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from django.core.files.storage import default_storage
from django.core.management import call_command
from django.utils import timezone

from .models import CMSPage, MediaAsset
from .versioning import create_page_version


def generate_media_derivatives(media_asset_id: int) -> dict[str, Any]:
    """
    Placeholder job for image/video/audio/document derivative generation.
    In a fuller implementation, this would create thumbnails, previews, waveforms, etc.
    """
    asset = MediaAsset.objects.get(pk=media_asset_id)

    result = {
        "media_asset_id": asset.id,
        "title": asset.title,
        "kind": asset.kind,
        "processed_at": timezone.now().isoformat(),
        "thumbnail_created": False,
        "metadata_extracted": False,
    }

    # Lightweight placeholder behavior:
    # - image/document kinds are flagged as derivative candidates
    if asset.kind in {"image", "document"}:
        result["thumbnail_created"] = True

    result["metadata_extracted"] = True
    return result


def export_page_snapshot(page_id: int, export_dir: str = "exports/pages") -> str:
    """
    Export a page snapshot JSON file asynchronously.
    """
    page = CMSPage.objects.get(pk=page_id)
    payload = {
        "page": {
            "id": page.id,
            "title": page.title,
            "slug": page.slug,
            "language": page.language,
            "layout": page.layout,
            "columns": page.columns,
            "is_public": page.is_public,
            "is_published": page.is_published,
            "updated_at": page.updated_at.isoformat() if page.updated_at else None,
        },
        "blocks": [
            {
                "id": block.id,
                "block_type": block.block_type.name,
                "position": block.position,
                "span": block.span,
                "span_order": block.span_order,
                "content": block.content,
                "config": block.config,
            }
            for block in page.blocks.select_related("block_type").order_by("position", "span_order")
        ],
    }

    filename = f"{export_dir}/page_{page.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.json"
    content = json.dumps(payload, indent=2, ensure_ascii=False)
    default_storage.save(filename, content.encode("utf-8"))
    return filename


def rebuild_search_index_for_page(page_id: int) -> dict[str, Any]:
    """
    Placeholder search indexing hook.
    If Haystack/Solr is wired for CMS pages later, this is the seam to use.
    """
    page = CMSPage.objects.get(pk=page_id)
    # Light placeholder: returns an indexing event payload.
    return {
        "page_id": page.id,
        "slug": page.slug,
        "language": page.language,
        "indexed_at": timezone.now().isoformat(),
        "status": "queued-placeholder",
    }


def create_large_page_snapshot(page_id: int, user_id: int | None = None, change_summary: str = "") -> dict[str, Any]:
    """
    Async snapshot hook for larger pages where synchronous snapshotting may become expensive.
    """
    page = CMSPage.objects.get(pk=page_id)
    user = None
    if user_id:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.filter(pk=user_id).first()

    version = create_page_version(page=page, user=user, change_summary=change_summary)
    return {
        "page_id": page.id,
        "version_id": version.id,
        "version_number": version.version_number,
    }


def refresh_search_index_full() -> str:
    """
    Optional heavier full-index job hook.
    """
    # Left intentionally as a command seam.
    # Uncomment if your standalone project wires CMS search into Haystack:
    # call_command("rebuild_index", interactive=False)
    return "search index refresh hook executed"
