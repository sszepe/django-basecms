from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import (
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)

from .models import CMSPage, PageVersion
from .version_api_serializers import (
    PageVersionSerializer,
    PageVersionCreateSerializer,
    PageVersionRestoreSerializer,
)
from .versioning import create_page_version, restore_page_version
from .openapi_examples import VERSION_SNAPSHOT_EXAMPLE, VERSION_RESTORE_EXAMPLE


class IsCockpitStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


@extend_schema_view(
    get=extend_schema(
        tags=["CMS Versions"],
        summary="List page versions",
        responses={200: PageVersionSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["CMS Versions"],
        summary="Create page snapshot",
        request=PageVersionCreateSerializer,
        responses={201: PageVersionSerializer},
        examples=[VERSION_SNAPSHOT_EXAMPLE],
    ),
)
class PageVersionsApi(APIView):
    permission_classes = [IsCockpitStaff]

    def get(self, request, page_id):
        page = get_object_or_404(CMSPage, pk=page_id)
        versions = page.versions.order_by("-version_number")
        return Response(PageVersionSerializer(versions, many=True).data)

    def post(self, request, page_id):
        page = get_object_or_404(CMSPage, pk=page_id)
        serializer = PageVersionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version = create_page_version(
            page=page,
            user=request.user,
            change_summary=serializer.validated_data.get("change_summary", ""),
        )
        return Response(PageVersionSerializer(version).data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["CMS Versions"],
    summary="Restore page version",
    request=PageVersionRestoreSerializer,
    responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Restore result")},
    examples=[VERSION_RESTORE_EXAMPLE],
)
class PageVersionRestoreApi(APIView):
    permission_classes = [IsCockpitStaff]

    def post(self, request, page_id, version_id):
        page = get_object_or_404(CMSPage, pk=page_id)
        version = get_object_or_404(PageVersion, pk=version_id, page=page)
        serializer = PageVersionRestoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        restore_page_version(page, version)
        return Response({"status": "restored", "version_number": version.version_number})
