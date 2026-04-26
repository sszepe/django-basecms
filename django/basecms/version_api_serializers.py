from rest_framework import serializers

from .models import PageVersion


class PageVersionSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = PageVersion
        fields = [
            "id",
            "page",
            "version_number",
            "title",
            "created_at",
            "created_by",
            "created_by_username",
            "change_summary",
        ]
        read_only_fields = ["version_number", "title", "created_at", "created_by", "created_by_username"]


class PageVersionCreateSerializer(serializers.Serializer):
    change_summary = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class PageVersionRestoreSerializer(serializers.Serializer):
    confirm = serializers.BooleanField()

    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError("You must confirm restoration.")
        return value
