from django.core.management.base import BaseCommand
from basecms.models import BlockType, CMSPage, NavbarItem, PageBlock

class Command(BaseCommand):
    help = "Seed a minimal basecms setup"

    def handle(self, *args, **options):
        block_types = [
            ("html", "HTML", "basecms/blocks/html.html"),
            ("asset", "Asset", "basecms/blocks/asset.html"),
            ("media_embed", "Media Embed", "basecms/blocks/media_embed.html"),
            ("pdf_viewer", "PDF Viewer", "basecms/blocks/pdf_viewer.html"),
            ("image_viewer", "Image Viewer", "basecms/blocks/image_viewer.html"),
            ("column", "Columns", "basecms/blocks/column.html"),
            ("page_title", "Page Title", "basecms/blocks/page_title.html"),
            ("line_break", "Line Break", "basecms/blocks/line_break.html"),
            ("list_of_pages", "List of Pages", "basecms/blocks/list_of_pages.html"),
        ]
        for name, label, template in block_types:
            BlockType.objects.get_or_create(name=name, defaults={"label": label, "template_name": template, "description": label})
        for language in ["en", "de"]:
            page, _ = CMSPage.objects.get_or_create(
                slug="index", language=language,
                defaults={"title": "Home" if language == "en" else "Startseite", "show_title": True, "layout": "vertical", "columns": 1, "is_public": True, "is_published": True},
            )
            html_type = BlockType.objects.get(name="html")
            if not page.blocks.exists():
                PageBlock.objects.create(page=page, block_type=html_type, position=0, span=1, span_order=0, content="<p>Welcome to basecms.</p>" if language == "en" else "<p>Willkommen bei basecms.</p>", config={"editor_mode": "visual"})
            NavbarItem.objects.get_or_create(title="Home" if language == "en" else "Start", language=language, cms_page=page, defaults={"sort_order": 0, "is_public": True})
        self.stdout.write(self.style.SUCCESS("Seeded basecms."))
