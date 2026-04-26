"""
views.py — utility view helpers.

CMSPageView, CMSPageListView and NavbarView live in public_views.py.
This module retains build_nav_tree (used by context_processors) and
BlockRenderer (used by template tags / future extensions).
"""
from .models import CMSPage, NavbarItem


def build_nav_tree(visible_items_queryset, user):
    """
    Build a nested tree of NavbarItems from a flat queryset.
    Items must already be filtered to what the user can see.
    Returns a list of root-level items, each with a .visible_children attribute.
    """
    items = list(
        visible_items_queryset
        .select_related("cms_page", "parent")
        .order_by("parent_id", "sort_order", "title")
    )
    by_parent: dict = {}
    for item in items:
        by_parent.setdefault(item.parent_id, []).append(item)

    def attach(parent_id=None, level=0):
        nodes = []
        for item in by_parent.get(parent_id, []):
            item.nav_level = level          # avoid clashing with the model @property
            item.visible_children = attach(item.id, level + 1)
            nodes.append(item)
        return nodes

    return attach(None, 0)


class BlockRenderer:
    """Dispatch helper for rendering block context in templates."""

    @staticmethod
    def render_block(block, context=None):
        context = context or {}
        context["block"] = block
        context["config"] = block.config or {}
        method_name = f"_render_{block.block_type.name}"
        if hasattr(BlockRenderer, method_name):
            context.update(getattr(BlockRenderer, method_name)(block))
        return context

    @staticmethod
    def _render_html(block):
        return {"html_content": block.content}

    @staticmethod
    def _render_image_viewer(block):
        # FIX: this method was missing — without it, `attachments` was never
        # added to the template context, so the template looped over nothing
        # and always showed "No images attached."
        return {
            "attachments": block.attachments.select_related("media_asset").all(),
        }

    @staticmethod
    def _render_pdf_viewer(block):
        # FIX: same issue as image_viewer — attachments missing from context
        return {
            "attachments": block.attachments.select_related("media_asset").all(),
        }

    @staticmethod
    def _render_asset(block):
        return {
            "attachments": block.attachments.select_related("media_asset").all(),
            "alignment": (block.config or {}).get("alignment", "center"),
            "show_metadata": (block.config or {}).get("show_metadata", True),
        }

    @staticmethod
    def _render_media_embed(block):
        return {
            "attachments": block.attachments.select_related("media_asset").all(),
            "alignment": (block.config or {}).get("alignment", "center"),
            "size": (block.config or {}).get("size", "medium"),
        }

    @staticmethod
    def _render_item_carousel(block):
        return {
            "attachments": block.attachments.select_related("media_asset").all(),
            "autoplay": (block.config or {}).get("autoplay", True),
            "interval": (block.config or {}).get("interval", 5000),
        }

    @staticmethod
    def _render_column(block):
        """
        Build context for column.html — passes columns with their nested blocks.

        FIX: use block.columns.all() (hits the prefetch cache set up by the view)
        and resolve nested blocks via col.nested_blocks.all() (also prefetched)
        instead of querying block.page.blocks which bypasses the prefetch and
        causes extra DB queries per column block.
        """
        columns = list(block.columns.order_by("order"))
        for col in columns:
            # nested_blocks is the related_name on BlockColumn → PageBlock.parent_column.
            # The view's prefetch_related("columns__nested_blocks__...") populates
            # this cache, so no extra queries are needed here.
            col._nested = list(
                col.nested_blocks.order_by("span_order")
                .select_related("block_type")
                .prefetch_related("attachments__media_asset", "columns")
            )
        return {"columns": columns}

    @staticmethod
    def _render_page_title(block):
        return {}

    @staticmethod
    def _render_page_datetime(block):
        return {"date_type": (block.config or {}).get("date_type", "updated")}

    @staticmethod
    def _render_line_break(block):
        return {"style": (block.config or {}).get("style", "solid")}

    @staticmethod
    def _render_list_of_pages(block):
        pages = CMSPage.objects.filter(
            language=block.page.language,
            is_published=True,
        ).order_by((block.config or {}).get("sort", "title"))
        return {"pages": pages}
