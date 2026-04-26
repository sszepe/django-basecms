from django.db import transaction
from django.shortcuts import get_object_or_404
from guardian.shortcuts import assign_perm
from rest_framework import permissions, status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import (
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)

from .models import (
    BlockAttachment,
    BlockColumn,
    BlockType,
    CMSPage,
    MediaAsset,
    NavbarItem,
    PageBlock,
)
from .api_serializers import (
    BlockAttachmentSerializer,
    BlockColumnSerializer,
    BlockColumnWriteSerializer,
    BlockTypeSerializer,
    CMSPageDetailSerializer,
    CMSPageListSerializer,
    MediaAssetSerializer,
    NavbarItemSerializer,
    PageBlockSerializer,
    PageBlockWriteSerializer,
)
from .openapi_examples import (
    PAGE_CREATE_EXAMPLE,
    PAGE_RESPONSE_EXAMPLE,
    HTML_BLOCK_CREATE_EXAMPLE,
    HTML_BLOCK_CONFIG_EXAMPLE,
    MEDIA_EMBED_BLOCK_CONFIG_EXAMPLE,
    COLUMN_BLOCK_CREATE_EXAMPLE,
    REORDER_BLOCKS_EXAMPLE,
    MEDIA_UPLOAD_MULTIPART_EXAMPLE,
    MEDIA_EXTERNAL_EXAMPLE,
    ATTACH_MEDIA_ASSET_EXAMPLE,
    ATTACH_EXTERNAL_URL_EXAMPLE,
    ATTACH_EMBED_EXAMPLE,
    NAVBAR_CREATE_EXAMPLE,
)

# ---------------------------------------------------------------------------
# Shared descriptions
# ---------------------------------------------------------------------------

CMS_SESSION_AUTH_DESCRIPTION = """
## Session authentication

This CMS API is intended for browser-based staff users.

Authentication flow:
1. Load the login page to receive a CSRF cookie.
2. POST credentials to `/accounts/login/`.
3. Send subsequent requests with the session cookie and `X-CSRFToken` header.
4. Use `/api/cockpit/auth/me/` to inspect the current authenticated session.
5. POST to `/accounts/logout/` to end the session.

The React cockpit uses session authentication with `credentials: include`.
"""

PAGE_ENDPOINT_NOTE = """
CMS pages are public-facing content objects rendered by Django templates on the public site.
A page is uniquely identified by `(slug, language)`.
"""

BLOCK_ENDPOINT_NOTE = """
Blocks define page layout and content units.
Important config examples:
- HTML block config: `editor_mode`
- media embed config: `alignment`, `size`, `autoplay`, `controls`
- column block config: `gap`, `stack_on_mobile`
"""

MEDIA_ENDPOINT_NOTE = """
Media assets support both uploaded files and external references.
Use multipart/form-data when sending a file.
"""


class IsStaffUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


# ---------------------------------------------------------------------------
# CMS Pages
# ---------------------------------------------------------------------------

@extend_schema_view(
    get=extend_schema(
        tags=["CMS Pages"],
        summary="List CMS pages",
        description=CMS_SESSION_AUTH_DESCRIPTION + "\n\n" + PAGE_ENDPOINT_NOTE,
        responses={200: CMSPageListSerializer(many=True)},
        examples=[PAGE_RESPONSE_EXAMPLE],
    ),
    post=extend_schema(
        tags=["CMS Pages"],
        summary="Create CMS page",
        description=CMS_SESSION_AUTH_DESCRIPTION + "\n\n" + PAGE_ENDPOINT_NOTE,
        request=CMSPageDetailSerializer,
        responses={201: CMSPageDetailSerializer},
        examples=[PAGE_CREATE_EXAMPLE, PAGE_RESPONSE_EXAMPLE],
    ),
)
class CMSPageListCreateApi(ListCreateAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = CMSPageListSerializer

    def get_queryset(self):
        qs = CMSPage.objects.all().order_by("language", "title")
        language = self.request.query_params.get("language")
        if language:
            qs = qs.filter(language=language)
        return qs

    def get_serializer_class(self):
        return CMSPageDetailSerializer if self.request.method == "POST" else CMSPageListSerializer

    def perform_create(self, serializer):
        page = serializer.save(created_by=self.request.user)
        if not page.is_public:
            assign_perm("view_cmspage", self.request.user, page)


@extend_schema_view(
    get=extend_schema(
        tags=["CMS Pages"],
        summary="Get CMS page",
        description=PAGE_ENDPOINT_NOTE,
        responses={200: CMSPageDetailSerializer},
        examples=[PAGE_RESPONSE_EXAMPLE],
    ),
    patch=extend_schema(
        tags=["CMS Pages"],
        summary="Update CMS page",
        description=PAGE_ENDPOINT_NOTE,
        request=CMSPageDetailSerializer,
        responses={200: CMSPageDetailSerializer},
        examples=[PAGE_CREATE_EXAMPLE, PAGE_RESPONSE_EXAMPLE],
    ),
)
class CMSPageDetailApi(RetrieveUpdateAPIView):
    permission_classes = [IsStaffUser]
    queryset = CMSPage.objects.all()
    serializer_class = CMSPageDetailSerializer


class CMSPagePublishApi(APIView):
    permission_classes = [IsStaffUser]
    serializer_class = None

    @extend_schema(
        tags=["CMS Pages"],
        summary="Publish page",
        description="Marks a page as published and sets its published timestamp.",
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Publish status")},
    )
    def post(self, request, pk):
        page = get_object_or_404(CMSPage, pk=pk)
        page.is_published = True
        page.save()
        return Response({"status": "published"})

    @extend_schema(
        tags=["CMS Pages"],
        summary="Unpublish page",
        description="Marks a page as unpublished.",
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Unpublish status")},
    )
    def delete(self, request, pk):
        page = get_object_or_404(CMSPage, pk=pk)
        page.is_published = False
        page.save()
        return Response({"status": "unpublished"})


# ---------------------------------------------------------------------------
# Block types
# ---------------------------------------------------------------------------

class BlockTypesApi(APIView):
    permission_classes = [IsStaffUser]

    @extend_schema(
        tags=["CMS Blocks"],
        summary="List block types",
        description="Returns available block types and their configuration schema.",
        responses={200: BlockTypeSerializer(many=True)},
    )
    def get(self, request):
        qs = BlockType.objects.filter(is_active=True).order_by("label")
        return Response(BlockTypeSerializer(qs, many=True).data)


# ---------------------------------------------------------------------------
# Page blocks
# ---------------------------------------------------------------------------

@extend_schema_view(
    get=extend_schema(
        tags=["CMS Blocks"],
        summary="List page blocks",
        description=BLOCK_ENDPOINT_NOTE,
        responses={200: PageBlockSerializer(many=True)},
        examples=[HTML_BLOCK_CONFIG_EXAMPLE, MEDIA_EMBED_BLOCK_CONFIG_EXAMPLE],
    ),
    post=extend_schema(
        tags=["CMS Blocks"],
        summary="Create block on page",
        description=BLOCK_ENDPOINT_NOTE,
        request=PageBlockWriteSerializer,
        responses={201: PageBlockSerializer},
        examples=[HTML_BLOCK_CREATE_EXAMPLE, COLUMN_BLOCK_CREATE_EXAMPLE],
    ),
)
class PageBlocksApi(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request, page_id):
        page = get_object_or_404(CMSPage, pk=page_id)
        blocks = (
            page.blocks
            .select_related("block_type")
            .prefetch_related("attachments__media_asset", "columns")
            .order_by("position", "span_order")
        )
        return Response(PageBlockSerializer(blocks, many=True).data)

    def post(self, request, page_id):
        page = get_object_or_404(CMSPage, pk=page_id)
        serializer = PageBlockWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        block = serializer.save(page=page)
        if block.block_type.name == "column":
            BlockColumn.objects.create(block=block, width=6, order=0)
            BlockColumn.objects.create(block=block, width=6, order=1)
        return Response(PageBlockSerializer(block).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    patch=extend_schema(
        tags=["CMS Blocks"],
        summary="Update block",
        description=BLOCK_ENDPOINT_NOTE,
        request=PageBlockWriteSerializer,
        responses={200: PageBlockSerializer},
        examples=[HTML_BLOCK_CREATE_EXAMPLE, HTML_BLOCK_CONFIG_EXAMPLE, MEDIA_EMBED_BLOCK_CONFIG_EXAMPLE],
    ),
    delete=extend_schema(
        tags=["CMS Blocks"],
        summary="Delete block",
        responses={204: OpenApiResponse(description="Block deleted")},
    ),
)
class BlockDetailApi(APIView):
    permission_classes = [IsStaffUser]

    def patch(self, request, pk):
        block = get_object_or_404(PageBlock, pk=pk)
        serializer = PageBlockWriteSerializer(block, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        block.refresh_from_db()
        return Response(PageBlockSerializer(block).data)

    def delete(self, request, pk):
        block = get_object_or_404(PageBlock, pk=pk)
        block.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DuplicateBlockApi(APIView):
    permission_classes = [IsStaffUser]
    serializer_class = None

    @extend_schema(
        tags=["CMS Blocks"],
        summary="Duplicate block",
        description="Duplicates a block, including its attachments.",
        responses={201: PageBlockSerializer},
    )
    def post(self, request, pk):
        source = get_object_or_404(PageBlock, pk=pk)
        clone = PageBlock.objects.create(
            page=source.page,
            block_type=source.block_type,
            position=source.position,
            span=source.span,
            span_order=source.span_order + 1,
            config=source.config,
            content=source.content,
            parent_column=source.parent_column,
        )
        for att in source.attachments.all():
            BlockAttachment.objects.create(
                block=clone,
                media_asset=att.media_asset,
                external_url=att.external_url,
                embed_code=att.embed_code,
                caption=att.caption,
                display_order=att.display_order,
                attachment_config=att.attachment_config,
            )
        return Response(PageBlockSerializer(clone).data, status=status.HTTP_201_CREATED)


class ReorderBlocksApi(APIView):
    permission_classes = [IsStaffUser]

    @extend_schema(
        tags=["CMS Blocks"],
        summary="Reorder blocks",
        description=(
            "Updates row position, span order, span width, and optional nested "
            "column placement for blocks."
        ),
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Reorder result")},
        examples=[REORDER_BLOCKS_EXAMPLE],
    )
    def post(self, request, page_id):
        blocks = request.data.get("blocks", [])
        with transaction.atomic():
            for item in blocks:
                PageBlock.objects.filter(id=item["id"], page_id=page_id).update(
                    position=item["position"],
                    span=item.get("span", 1),
                    span_order=item.get("span_order", 0),
                    parent_column=item.get("parent_column"),
                )
        return Response({"success": True})


class ColumnDetailApi(APIView):
    permission_classes = [IsStaffUser]

    @extend_schema(
        tags=["CMS Blocks"],
        summary="Update column",
        description="Updates width and alignment settings for a column inside a column block.",
        request=BlockColumnWriteSerializer,
        responses={200: BlockColumnSerializer},
    )
    def patch(self, request, pk):
        column = get_object_or_404(BlockColumn, pk=pk)
        serializer = BlockColumnWriteSerializer(column, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        column.refresh_from_db()
        return Response(BlockColumnSerializer(column).data)


# ---------------------------------------------------------------------------
# Media assets
# ---------------------------------------------------------------------------

@extend_schema_view(
    get=extend_schema(
        tags=["CMS Media"],
        summary="List media assets",
        description=MEDIA_ENDPOINT_NOTE,
        responses={200: MediaAssetSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["CMS Media"],
        summary="Create media asset",
        description=MEDIA_ENDPOINT_NOTE,
        request=MediaAssetSerializer,
        responses={201: MediaAssetSerializer},
        examples=[MEDIA_UPLOAD_MULTIPART_EXAMPLE, MEDIA_EXTERNAL_EXAMPLE],
    ),
)
class MediaAssetsApi(ListCreateAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = MediaAssetSerializer
    queryset = MediaAsset.objects.all().order_by("-created_at")

    def get(self, request, *args, **kwargs):
        q = request.query_params.get("q", "").strip()
        qs = self.get_queryset()
        if q:
            qs = qs.filter(title__icontains=q)
        return Response(self.get_serializer(qs, many=True).data)


class BlockAttachmentsApi(APIView):
    permission_classes = [IsStaffUser]

    @extend_schema(
        tags=["CMS Media"],
        summary="Attach media to block",
        description="Attaches exactly one of: media asset, external URL, or embed code.",
        request=BlockAttachmentSerializer,
        responses={201: BlockAttachmentSerializer},
        examples=[ATTACH_MEDIA_ASSET_EXAMPLE, ATTACH_EXTERNAL_URL_EXAMPLE, ATTACH_EMBED_EXAMPLE],
    )
    def post(self, request, block_id):
        block = get_object_or_404(PageBlock, pk=block_id)
        attachment = BlockAttachment.objects.create(
            block=block,
            media_asset_id=request.data.get("media_asset"),
            external_url=request.data.get("external_url"),
            embed_code=request.data.get("embed_code", ""),
            caption=request.data.get("caption", ""),
            display_order=request.data.get("display_order", 0),
            attachment_config=request.data.get("attachment_config", {}),
        )
        return Response(BlockAttachmentSerializer(attachment).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    patch=extend_schema(
        tags=["CMS Media"],
        summary="Update block attachment",
        request=BlockAttachmentSerializer,
        responses={200: BlockAttachmentSerializer},
    ),
    delete=extend_schema(
        tags=["CMS Media"],
        summary="Delete block attachment",
        responses={204: OpenApiResponse(description="Attachment deleted")},
    ),
)
class AttachmentDetailApi(APIView):
    permission_classes = [IsStaffUser]

    def patch(self, request, pk):
        attachment = get_object_or_404(BlockAttachment, pk=pk)
        serializer = BlockAttachmentSerializer(attachment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        attachment.refresh_from_db()
        return Response(BlockAttachmentSerializer(attachment).data)

    def delete(self, request, pk):
        attachment = get_object_or_404(BlockAttachment, pk=pk)
        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Navbar
# ---------------------------------------------------------------------------

@extend_schema_view(
    get=extend_schema(
        tags=["CMS Navigation"],
        summary="List navbar items",
        responses={200: NavbarItemSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["CMS Navigation"],
        summary="Create navbar item",
        request=NavbarItemSerializer,
        responses={201: NavbarItemSerializer},
        examples=[NAVBAR_CREATE_EXAMPLE],
    ),
)
class NavbarItemsApi(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        language = request.GET.get("language")
        qs = NavbarItem.objects.select_related("cms_page", "parent").order_by("language", "parent_id", "sort_order", "title")
        if language:
            qs = qs.filter(language=language)
        return Response(NavbarItemSerializer(qs, many=True).data)

    def post(self, request):
        serializer = NavbarItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        return Response(NavbarItemSerializer(item).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    patch=extend_schema(
        tags=["CMS Navigation"],
        summary="Update navbar item",
        request=NavbarItemSerializer,
        responses={200: NavbarItemSerializer},
        examples=[NAVBAR_CREATE_EXAMPLE],
    ),
    delete=extend_schema(
        tags=["CMS Navigation"],
        summary="Delete navbar item",
        responses={204: OpenApiResponse(description="Navbar item deleted")},
    ),
)
class NavbarItemDetailApi(APIView):
    permission_classes = [IsStaffUser]

    def patch(self, request, pk):
        item = get_object_or_404(NavbarItem, pk=pk)
        serializer = NavbarItemSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        item.refresh_from_db()
        return Response(NavbarItemSerializer(item).data)

    def delete(self, request, pk):
        item = get_object_or_404(NavbarItem, pk=pk)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Auth session info
# ---------------------------------------------------------------------------

class SessionInfoApi(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Get current session info",
        description=CMS_SESSION_AUTH_DESCRIPTION,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Session info")},
    )
    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"authenticated": False})
        return Response({
            "authenticated": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
            },
        })
