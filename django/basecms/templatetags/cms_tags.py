"""
cms_tags — template tags for rendering CMS page blocks.

Usage in templates:
    {% load cms_tags %}
    {% render_block block %}
    {{ blocks|top_level_blocks }}
"""
from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from basecms.views import BlockRenderer

register = template.Library()


@register.filter
def top_level_blocks(blocks):
    """Return only blocks that are not nested inside a column."""
    return [b for b in blocks if not b.parent_column_id]


@register.simple_tag(takes_context=True)
def render_block(context, block):
    """
    Render a PageBlock using its block_type template.

    The BlockRenderer builds a context dict for the block; we then render
    the template named in block.block_type.template_name.

    FIX: the return value must be wrapped in mark_safe().
    render_to_string() returns a plain str — Django's template engine will
    HTML-escape it when the simple_tag inserts it into the parent template,
    turning all <tags> into &lt;tags&gt; and rendering blocks as raw text or
    nothing at all. mark_safe() tells Django the HTML is already safe to
    insert verbatim.
    """
    block_context = BlockRenderer.render_block(
        block, context={"request": context.get("request")}
    )
    template_name = block.block_type.template_name

    try:
        html = render_to_string(template_name, block_context, request=context.get("request"))
        return mark_safe(html)
    except Exception as exc:
        # Surface the error in DEBUG so template problems are visible.
        from django.conf import settings
        if settings.DEBUG:
            return mark_safe(
                f'<div class="alert alert-danger">'
                f'<strong>Block render error</strong> ({block.block_type.name}): {exc}'
                f'</div>'
            )
        return mark_safe(block.content or "")
