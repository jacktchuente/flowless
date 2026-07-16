from tv_channel.models import GridBlock
from rest_framework import serializers

from tv_channel.services.editorial_rules_validation import validate_editorial_rules_payload


class GridBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = GridBlock
        fields = ("id", "grid_layout", "starts_at", "ends_at", "priority", "min_items", "max_items",
                  "min_duration_seconds_per_item", "max_duration_seconds_per_item",
                  "allowed", "preferred", "forbidden", "post_filler_policy",)


class GridBlockWriteSerializer(GridBlockSerializer):
    def validate_grid_layout(self, value):
        if self.instance is not None and value.pk != self.instance.grid_layout_id:
            raise serializers.ValidationError("Grid layout cannot be changed.")
        return value

    def validate(self, attrs):
        combined = {}
        if self.instance is not None:
            combined = {field: getattr(self.instance, field) for field in self.Meta.fields if field != "id"}
        combined.update(attrs)
        try:
            combined = validate_editorial_rules_payload(combined)
        except Exception as exc:
            from django.core.exceptions import ValidationError as DjangoValidationError
            if isinstance(exc, DjangoValidationError):
                raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
            raise
        if combined.get("starts_at") is not None and combined.get("ends_at") is not None and combined["starts_at"] >= combined["ends_at"]:
            raise serializers.ValidationError({"ends_at": "Must be later than starts_at."})
        priority = combined.get("priority", 50)
        if not 0 <= priority <= 100:
            raise serializers.ValidationError({"priority": "Must be between 0 and 100."})
        min_items, max_items = combined.get("min_items", 1), combined.get("max_items", 1)
        if min_items < 1:
            raise serializers.ValidationError({"min_items": "Must be at least 1."})
        if max_items > 3:
            raise serializers.ValidationError({"max_items": "Must be at most 3."})
        if min_items > max_items:
            raise serializers.ValidationError({"max_items": "Must be greater than or equal to min_items."})
        min_duration = combined.get("min_duration_seconds_per_item")
        max_duration = combined.get("max_duration_seconds_per_item")
        for field, value in (("min_duration_seconds_per_item", min_duration), ("max_duration_seconds_per_item", max_duration)):
            if value is not None and value <= 0:
                raise serializers.ValidationError({field: "Must be greater than 0."})
        if min_duration is not None and max_duration is not None and min_duration > max_duration:
            raise serializers.ValidationError({"max_duration_seconds_per_item": "Must be greater than or equal to the minimum duration."})
        return {key: combined[key] for key in attrs}
