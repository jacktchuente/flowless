from rest_framework import serializers

from tv_channel.models import EditorialLine


class EditorialLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = EditorialLine
        fields = (
            "allowed_categories",
            "forbidden_categories",
            "preferred_categories",
            "allowed_natures",
            "forbidden_natures",
            "preferred_natures",
            "allowed_container_kinds",
            "forbidden_container_kinds",
            "preferred_container_kinds",
            "start_at",
            "end_at",
            "allow_filler",
        )
