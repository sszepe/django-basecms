from copy import deepcopy
from typing import Any

from django.db import transaction

from .models import CMSPage, PageVersion, PageBlock, BlockAttachment, BlockColumn


def snapshot_page(page: CMSPage) -> dict[str, Any]:
    """Capture a complete serialisable snapshot of a page and all its blocks."""
    blocks = []
    for block in (
        page.blocks
        .select_related("block_type", "parent_column__block")
        .prefetch_related("attachments__media_asset", "columns")
        .order_by("position", "span_order")
    ):
        block_data: dict[str, Any] = {
            "block_type_id": block.block_type_id,
            "position": block.position,
            "span": block.span,
            "span_order": block.span_order,
            "config": deepcopy(block.config or {}),
            "content": block.content,
            # Store parent identification as (parent_block_position, column_order)
            # so we can uniquely re-link after restore without relying on PKs.
            "parent_ref": None,
            "columns": [],
            "attachments": [],
        }

        if block.parent_column_id:
            block_data["parent_ref"] = {
                "block_position": block.parent_column.block.position,
                "column_order": block.parent_column.order,
            }

        for column in block.columns.all().order_by("order"):
            block_data["columns"].append({
                "order": column.order,
                "width": column.width,
                "horizontal_align": column.horizontal_align,
                "vertical_align": column.vertical_align,
                "css_class": column.css_class,
                "background_color": column.background_color,
                "padding": column.padding,
            })

        for attachment in block.attachments.all().order_by("display_order"):
            block_data["attachments"].append({
                "media_asset_id": attachment.media_asset_id,
                "external_url": attachment.external_url,
                "embed_code": attachment.embed_code,
                "caption": attachment.caption,
                "display_order": attachment.display_order,
                "attachment_config": deepcopy(attachment.attachment_config or {}),
            })

        blocks.append(block_data)

    return {
        "page": {
            "title": page.title,
            "content": page.content,
            "language": page.language,
            "show_title": page.show_title,
            "layout": page.layout,
            "columns": page.columns,
            "is_public": page.is_public,
            "is_published": page.is_published,
        },
        "blocks": blocks,
    }


def create_page_version(page: CMSPage, user=None, change_summary: str = "") -> PageVersion:
    latest = page.versions.order_by("-version_number").first()
    version_number = 1 if latest is None else latest.version_number + 1
    snapshot = snapshot_page(page)

    return PageVersion.objects.create(
        page=page,
        version_number=version_number,
        title=page.title,
        content_snapshot=snapshot,
        created_by=user,
        change_summary=change_summary or "",
    )


def _create_attachments(block: PageBlock, attachments_data: list) -> None:
    for att in attachments_data:
        BlockAttachment.objects.create(
            block=block,
            media_asset_id=att.get("media_asset_id"),
            external_url=att.get("external_url"),
            embed_code=att.get("embed_code", ""),
            caption=att.get("caption", ""),
            display_order=att.get("display_order", 0),
            attachment_config=att.get("attachment_config", {}),
        )


@transaction.atomic
def restore_page_version(page: CMSPage, version: PageVersion) -> CMSPage:
    snapshot = version.content_snapshot
    page_data = snapshot.get("page", {})
    blocks_data = snapshot.get("blocks", [])

    # Restore page metadata
    for field in ("title", "content", "language", "show_title", "layout", "columns", "is_public", "is_published"):
        if field in page_data:
            setattr(page, field, page_data[field])
    page.save()

    # Wipe existing blocks (cascade deletes columns & attachments)
    page.blocks.all().delete()

    # Pass 1 — create top-level blocks; build lookup keyed by position
    # Key: position (int) → (block, {column_order: BlockColumn})
    top_level_map: dict[int, tuple[PageBlock, dict[int, BlockColumn]]] = {}

    for block_data in blocks_data:
        if block_data.get("parent_ref") is not None:
            continue  # handled in pass 2

        block = PageBlock.objects.create(
            page=page,
            block_type_id=block_data["block_type_id"],
            position=block_data["position"],
            span=block_data["span"],
            span_order=block_data["span_order"],
            config=block_data.get("config", {}),
            content=block_data.get("content", ""),
            parent_column=None,
        )

        column_map: dict[int, BlockColumn] = {}
        for column_data in block_data.get("columns", []):
            col = BlockColumn.objects.create(
                block=block,
                order=column_data["order"],
                width=column_data["width"],
                horizontal_align=column_data.get("horizontal_align", "start"),
                vertical_align=column_data.get("vertical_align", "start"),
                css_class=column_data.get("css_class", ""),
                background_color=column_data.get("background_color", ""),
                padding=column_data.get("padding", "3"),
            )
            column_map[col.order] = col

        _create_attachments(block, block_data.get("attachments", []))
        top_level_map[block.position] = (block, column_map)

    # Pass 2 — create nested blocks, resolving parent_ref
    for block_data in blocks_data:
        parent_ref = block_data.get("parent_ref")
        if parent_ref is None:
            continue

        parent_position = parent_ref["block_position"]
        column_order = parent_ref["column_order"]

        parent_entry = top_level_map.get(parent_position)
        target_column = parent_entry[1].get(column_order) if parent_entry else None

        block = PageBlock.objects.create(
            page=page,
            block_type_id=block_data["block_type_id"],
            position=block_data["position"],
            span=block_data["span"],
            span_order=block_data["span_order"],
            config=block_data.get("config", {}),
            content=block_data.get("content", ""),
            parent_column=target_column,
        )
        _create_attachments(block, block_data.get("attachments", []))

    return page
