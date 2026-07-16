from rest_framework import serializers

from tv_channel.models import EditorialLine
from tv_channel.services.editorial_rules_validation import validate_editorial_rules_payload


class EditorialLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = EditorialLine
        fields = (
            "allowed",
            "preferred",
            "forbidden",
            "start_at",
            "end_at",
            "allow_filler",
        )


class EditorialLineWriteSerializer(EditorialLineSerializer):
    def validate(self, attrs):
        combined = {}
        if self.instance is not None:
            combined = {field: getattr(self.instance, field) for field in self.Meta.fields}
        combined.update(attrs)
        try:
            normalized = validate_editorial_rules_payload(combined)
        except Exception as exc:
            from django.core.exceptions import ValidationError as DjangoValidationError
            if isinstance(exc, DjangoValidationError):
                raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
            raise
        if normalized.get("start_at") is not None and normalized.get("end_at") is not None and normalized["start_at"] >= normalized["end_at"]:
            raise serializers.ValidationError({"end_at": "Must be later than start_at."})
        return {key: normalized[key] for key in attrs}
