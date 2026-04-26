from .theme import get_theme

def basecms_theme(request):
    theme = get_theme()
    return {
        "basecms_theme": theme,
        "basecms_header_template": theme.header_template,
        "basecms_footer_template": theme.footer_template,
    }
