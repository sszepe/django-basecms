import re
from django.conf import settings
from django.shortcuts import redirect
from django.utils.translation import get_language_from_request

class CMSRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.excluded_paths = getattr(settings, "CMS_REDIRECT_EXCLUDE_PATHS", [])

    def __call__(self, request):
        if any(re.match(f"^{pattern}", request.path) for pattern in self.excluded_paths):
            return self.get_response(request)

        if request.path.endswith("/index") or request.path.endswith("/index/"):
            return self.get_response(request)

        response = self.get_response(request)
        if response.status_code == 404:
            user_lang = get_language_from_request(request, check_path=False)[:2]
            available = [code[:2] for code, _ in settings.AVAILABLE_LANGUAGES]
            lang = user_lang if user_lang in available else available[0]
            parts = request.path.strip("/").split("/")
            if parts and parts[0] in available:
                return response
            redirect_url = f"/{lang}/index"
            if request.path != redirect_url:
                return redirect(redirect_url)
        return response
