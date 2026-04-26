from django.urls import path
from .version_api_views import PageVersionsApi, PageVersionRestoreApi

urlpatterns = [
    path("pages/<int:page_id>/versions/", PageVersionsApi.as_view(), name="cockpit_cms_page_versions"),
    path("pages/<int:page_id>/versions/<int:version_id>/restore/", PageVersionRestoreApi.as_view(), name="cockpit_cms_page_version_restore"),
]
