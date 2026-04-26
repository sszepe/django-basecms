"""
cms_react_tags — Template tags for embedding Vite-built assets.

In development  (DEBUG=True):  serves from Vite dev server on port 5173.
In production   (DEBUG=False): reads dist/.vite/manifest.json (Vite 5+)
                                or dist/manifest.json (Vite 4) to resolve
                                content-hashed filenames.

Usage in templates:
    {% load cms_react_tags %}
    {% vite_asset 'site' 'js' %}   → <script type="module" src="...">
    {% vite_asset 'site' 'css' %}  → <link rel="stylesheet" href="...">
"""
import json
from pathlib import Path
from typing import Optional

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()

# Vite 5 writes manifest to .vite/manifest.json; Vite 4 wrote manifest.json
_MANIFEST_CANDIDATES = [
    Path(settings.STATIC_ROOT) / ".vite" / "manifest.json",
    Path(settings.STATIC_ROOT) / "manifest.json",
]

# FIX: use a sentinel (None = not loaded yet, {} = loaded but empty).
# The old code set _manifest_cache = {} permanently when the file wasn't found
# yet. Since nginx copies the manifest into the volume AFTER Django starts,
# the first request always missed the file and cached the empty dict forever —
# meaning no subsequent request ever saw the manifest even after nginx wrote it.
# Now we only cache a non-empty manifest; if the file isn't found we return {}
# without caching it, so the next request retries.
_manifest_cache: Optional[dict] = None


def _load_manifest() -> dict:
    global _manifest_cache
    if _manifest_cache is not None:
        # Already successfully loaded — return the cached result.
        return _manifest_cache
    for candidate in _MANIFEST_CANDIDATES:
        if candidate.exists():
            data = json.loads(candidate.read_text())
            if data:
                # Only cache once we have a non-empty manifest.
                _manifest_cache = data
            return data
    # Manifest not found yet — return empty WITHOUT caching so the next
    # request retries (nginx may not have copied it yet on first boot).
    return {}


@register.simple_tag
def vite_asset(entry: str, asset_type: str) -> str:
    """
    Render the <script> or <link> tag(s) for a Vite entry.

    Args:
        entry:      entry name, e.g. 'site' or 'cockpit'
        asset_type: 'js' or 'css'
    """

    # ── Development: point at Vite HMR dev server ────────────────────────────
    if settings.DEBUG:
        dev_port = getattr(settings, "VITE_DEV_PORT", 5173)
        dev_origin = f"http://localhost:{dev_port}"
        if asset_type == "js":
            return mark_safe(
                f'<script type="module" src="{dev_origin}/@vite/client"></script>\n'
                f'<script type="module" src="{dev_origin}/src/{entry}.tsx"></script>'
            )
        # CSS injected by Vite HMR in dev — no separate tag needed
        return mark_safe("")

    # ── Production: resolve via manifest ─────────────────────────────────────
    manifest = _load_manifest()
    entry_key = f"src/{entry}.tsx"
    entry_data = manifest.get(entry_key, {})

    if asset_type == "js":
        file_path = entry_data.get("file", "")
        if not file_path:
            return mark_safe(f"<!-- vite: entry '{entry}' not found in manifest -->")
        src = f"/{file_path}"  # served by nginx /assets/ location
        # Also include any dynamically-imported chunks declared as imports
        imports = entry_data.get("imports", [])
        preload_tags = "".join(
            f'<link rel="modulepreload" href="/{manifest[k]["file"]}" />\n'
            for k in imports
            if k in manifest and "file" in manifest[k]
        )
        return mark_safe(
            f'{preload_tags}'
            f'<script type="module" src="{src}"></script>'
        )

    if asset_type == "css":
        css_files = entry_data.get("css", [])
        # Also collect CSS from imported chunks
        imports = entry_data.get("imports", [])
        for k in imports:
            css_files = css_files + manifest.get(k, {}).get("css", [])
        tags = "".join(
            f'<link rel="stylesheet" href="/{f}" />\n'
            for f in css_files
        )
        return mark_safe(tags or "")

    return mark_safe("")
