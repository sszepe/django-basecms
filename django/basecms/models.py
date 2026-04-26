from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.core.validators import MinValueValidator, MaxValueValidator
from guardian.shortcuts import get_objects_for_user


class CMSPage(models.Model):
    LAYOUT_CHOICES = [
        ("grid", "Grid"),
        ("vertical", "Vertical"),
    ]

    slug = models.SlugField()
    title = models.CharField(max_length=255)
    content = models.TextField(null=True, blank=True)
    language = models.CharField(max_length=10, choices=settings.AVAILABLE_LANGUAGES)
    show_title = models.BooleanField(default=True)
    layout = models.CharField(max_length=50, choices=LAYOUT_CHOICES, default="vertical")
    columns = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_cms_pages",
    )
    is_published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    is_public = models.BooleanField(default=True, db_index=True)

    class Meta:
        unique_together = ("slug", "language")
        ordering = ["slug", "language"]
        verbose_name = "CMS Page"
        verbose_name_plural = "CMS Pages"
        indexes = [
            models.Index(fields=["language", "is_published"]),
            models.Index(fields=["language", "slug"]),
        ]

    def __str__(self):
        return self.title

    def get_blocks_ordered(self):
        return self.blocks.order_by("position", "span_order")

    @classmethod
    def get_visible_pages_for_user(cls, user, language=None, published_only=True):
        queryset = cls.objects.all()
        if language:
            queryset = queryset.filter(language=language)
        if published_only:
            queryset = queryset.filter(is_published=True)

        if user.is_anonymous:
            return queryset.filter(is_public=True)
        if user.is_superuser:
            return queryset

        permitted_pages = get_objects_for_user(
            user,
            "basecms.view_cmspage",
            klass=queryset,
            accept_global_perms=False,
        )
        public_pages = queryset.filter(is_public=True)
        return (public_pages | permitted_pages).distinct()

    def user_can_view(self, user):
        if not self.is_published and not (hasattr(user, "is_superuser") and user.is_superuser):
            return False
        if self.is_public:
            return True
        if user.is_anonymous:
            return False
        if user.is_superuser:
            return True
        return user.has_perm("view_cmspage", self)

    def save(self, *args, **kwargs):
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        elif not self.is_published:
            self.published_at = None
        super().save(*args, **kwargs)


class NavbarItem(models.Model):
    title = models.CharField(max_length=255, help_text="Custom name for the link")
    language = models.CharField(
        max_length=10,
        choices=settings.AVAILABLE_LANGUAGES,
        default=settings.AVAILABLE_LANGUAGES[0][0],
        db_index=True,
        help_text="Language for this navbar item",
    )
    cms_page = models.ForeignKey(
        "CMSPage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="navbar_items",
        help_text="Select a CMS page (optional)",
    )
    external_url = models.URLField(blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0, help_text="Determines the order of the links")
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        help_text="The parent of this item",
    )
    is_public = models.BooleanField(default=True)

    class Meta:
        verbose_name = "NavbarItem"
        verbose_name_plural = "NavbarItems"
        ordering = ["language", "parent_id", "sort_order", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["language", "parent", "sort_order", "title"],
                name="basecms_navbaritem_lang_parent_sort_title_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["language", "parent_id", "sort_order"]),
        ]

    def __str__(self):
        return self.title

    @property
    def level(self) -> int:
        """Return nesting depth. Uses prefetched/cached parent chain to avoid N+1."""
        depth = 0
        node = self.parent
        seen: set[int] = set()
        while node is not None and node.pk not in seen:
            seen.add(node.pk)
            depth += 1
            node = node.parent
        return depth

    def get_ordered_children(self):
        return self.children.all().order_by("sort_order", "title")

    def get_visible_children_for_user(self, user):
        qs = self.get_ordered_children()
        if user.is_anonymous:
            return [item for item in qs if item.is_public]
        if user.is_superuser:
            return list(qs)
        return [item for item in qs if item.user_can_view(user)]

    @classmethod
    def get_visible_items_for_user(cls, user, language=None):
        queryset = cls.objects.select_related("parent", "cms_page")
        if language:
            queryset = queryset.filter(language=language)

        if user.is_anonymous:
            return queryset.filter(is_public=True)
        if user.is_superuser:
            return queryset

        permitted_items = get_objects_for_user(
            user,
            "basecms.view_navbaritem",
            klass=queryset,
            accept_global_perms=False,
        )
        public_items = queryset.filter(is_public=True)
        return (public_items | permitted_items).distinct()

    def user_can_view(self, user):
        if self.is_public:
            return True
        if user.is_anonymous:
            return False
        if user.is_superuser:
            return True
        return user.has_perm("view_navbaritem", self)


class NavbarCacheVersion:
    @staticmethod
    def get_version(language: str) -> int:
        key = f"navbar_cache_version_{language}"
        version = cache.get(key)
        if version is None:
            version = 1
            cache.set(key, version, None)
        return version

    @staticmethod
    def increment_version(language: str) -> int:
        key = f"navbar_cache_version_{language}"
        try:
            new_version = cache.incr(key)
        except ValueError:
            # key doesn't exist yet
            new_version = 1
            cache.set(key, new_version, None)
        return new_version


class BlockType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    label = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    template_name = models.CharField(max_length=255)
    icon_class = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    config_schema = models.JSONField(default=dict)

    class Meta:
        ordering = ["label"]

    def __str__(self):
        return self.label


class PageBlock(models.Model):
    page = models.ForeignKey(CMSPage, on_delete=models.CASCADE, related_name="blocks")
    block_type = models.ForeignKey(BlockType, on_delete=models.PROTECT, related_name="instances")
    position = models.IntegerField(default=0)
    span = models.IntegerField(default=1)
    span_order = models.IntegerField(default=0)
    config = models.JSONField(default=dict, null=True, blank=True)
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    parent_column = models.ForeignKey(
        "BlockColumn",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="nested_blocks",
    )

    class Meta:
        ordering = ["position", "span_order"]
        indexes = [
            models.Index(fields=["page", "position"]),
            models.Index(fields=["page", "parent_column"]),
        ]

    def __str__(self):
        return f"{self.block_type.label} on {self.page.title} (pos: {self.position})"

    def is_column_block(self):
        return self.block_type.name == "column"


class MediaAsset(models.Model):
    KIND_CHOICES = [
        ("image", "Image"),
        ("video", "Video"),
        ("audio", "Audio"),
        ("document", "Document"),
        ("embed", "Embed"),
    ]
    title = models.CharField(max_length=255)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="image", db_index=True)
    file = models.FileField(upload_to="media_assets/", null=True, blank=True)
    mime_type = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    source_url = models.URLField(blank=True)
    external_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class BlockAttachment(models.Model):
    block = models.ForeignKey(PageBlock, on_delete=models.CASCADE, related_name="attachments")
    media_asset = models.ForeignKey(
        MediaAsset,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="block_attachments",
    )
    external_url = models.URLField(blank=True, null=True)
    embed_code = models.TextField(blank=True)
    caption = models.TextField(blank=True)
    display_order = models.IntegerField(default=0)
    attachment_config = models.JSONField(default=dict)

    class Meta:
        ordering = ["display_order"]

    def __str__(self):
        if self.media_asset:
            return f"Asset: {self.media_asset.title} on block {self.block_id}"
        if self.external_url:
            return f"URL attachment on block {self.block_id}"
        return f"Embed attachment on block {self.block_id}"


class BlockItemQuery(models.Model):
    block = models.OneToOneField(PageBlock, on_delete=models.CASCADE, related_name="item_query")
    entity_type = models.CharField(max_length=255, blank=True)
    limit = models.IntegerField(default=10)
    sort_field = models.CharField(max_length=255, default="created_at")
    sort_order = models.CharField(
        max_length=10,
        choices=[("asc", "Ascending"), ("desc", "Descending")],
        default="desc",
    )
    filters = models.JSONField(default=dict)


class PageVersion(models.Model):
    page = models.ForeignKey(CMSPage, on_delete=models.CASCADE, related_name="versions")
    version_number = models.IntegerField()
    title = models.CharField(max_length=255)
    content_snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    change_summary = models.TextField(blank=True)

    class Meta:
        ordering = ["-version_number"]
        unique_together = ("page", "version_number")
        indexes = [
            models.Index(fields=["page", "-version_number"]),
        ]

    def __str__(self):
        return f"{self.page.title} v{self.version_number}"


class BlockTemplate(models.Model):
    name = models.CharField(max_length=255)
    block_type = models.ForeignKey(BlockType, on_delete=models.CASCADE)
    config_template = models.JSONField()
    content_template = models.TextField(blank=True)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name


class BlockColumn(models.Model):
    HORIZONTAL_ALIGN_CHOICES = [
        ("start", "Start (Left)"),
        ("center", "Center"),
        ("end", "End (Right)"),
    ]
    VERTICAL_ALIGN_CHOICES = [
        ("start", "Top"),
        ("center", "Middle"),
        ("end", "Bottom"),
        ("stretch", "Stretch"),
    ]

    block = models.ForeignKey(PageBlock, on_delete=models.CASCADE, related_name="columns")
    width = models.IntegerField(default=6, validators=[MinValueValidator(1), MaxValueValidator(12)])
    order = models.IntegerField(default=0)
    horizontal_align = models.CharField(
        max_length=10, choices=HORIZONTAL_ALIGN_CHOICES, default="start"
    )
    vertical_align = models.CharField(
        max_length=10, choices=VERTICAL_ALIGN_CHOICES, default="start"
    )
    css_class = models.CharField(max_length=255, blank=True)
    background_color = models.CharField(max_length=50, blank=True)
    padding = models.CharField(max_length=50, blank=True, default="3")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]
        indexes = [models.Index(fields=["block", "order"])]

    def __str__(self):
        return f"Column {self.order} (w={self.width}) of block {self.block_id}"


class ColumnBlockConfig(models.Model):
    GAP_CHOICES = [
        ("0", "No Gap"), ("1", "Extra Small"), ("2", "Small"),
        ("3", "Medium"), ("4", "Large"), ("5", "Extra Large"),
    ]
    ROW_ALIGN_CHOICES = [
        ("start", "Start"), ("center", "Center"), ("end", "End"),
        ("around", "Space Around"), ("between", "Space Between"), ("evenly", "Space Evenly"),
    ]

    block = models.OneToOneField(PageBlock, on_delete=models.CASCADE, related_name="column_config")
    gap = models.CharField(max_length=2, choices=GAP_CHOICES, default="3")
    row_horizontal_align = models.CharField(max_length=10, choices=ROW_ALIGN_CHOICES, default="start")
    stack_on_mobile = models.BooleanField(default=True)
    row_css_class = models.CharField(max_length=255, blank=True)
    row_background_color = models.CharField(max_length=50, blank=True)
    row_padding = models.CharField(max_length=50, blank=True, default="3")
    row_margin = models.CharField(max_length=50, blank=True, default="0")

    def __str__(self):
        return f"ColumnConfig for block {self.block_id}"
