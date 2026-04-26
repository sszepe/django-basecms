from dataclasses import dataclass, field
from django.conf import settings

@dataclass
class BaseCmsTheme:
    site_title: str = "basecms"
    site_subtitle: str = "Public content portal"
    footer_text: str = "© basecms"
    footer_links: list[tuple[str, str]] = field(default_factory=list)
    header_template: str = "includes/header.html"
    footer_template: str = "includes/footer.html"
    show_login_link: bool = True
    show_cms_link_for_staff: bool = True

def get_theme() -> BaseCmsTheme:
    cfg = getattr(settings, "BASECMS_THEME", {})
    return BaseCmsTheme(
        site_title=cfg.get("site_title", "basecms"),
        site_subtitle=cfg.get("site_subtitle", "Public content portal"),
        footer_text=cfg.get("footer_text", "© basecms"),
        footer_links=cfg.get("footer_links", []),
        header_template=cfg.get("header_template", "includes/header.html"),
        footer_template=cfg.get("footer_template", "includes/footer.html"),
        show_login_link=cfg.get("show_login_link", True),
        show_cms_link_for_staff=cfg.get("show_cms_link_for_staff", True),
    )
