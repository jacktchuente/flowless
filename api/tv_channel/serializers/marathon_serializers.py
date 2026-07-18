from rest_framework import serializers

from media_source.constants import MediaContainerKind
from tv_channel.models import MarathonKindPolicy


class MarathonKindPolicySerializer(serializers.ModelSerializer):
    container_kind_label = serializers.CharField(source="get_container_kind_display", read_only=True)

    class Meta:
        model = MarathonKindPolicy
        fields = ("container_kind", "container_kind_label", "min_run", "max_run", "quota")


class MarathonConfigSerializer(serializers.Serializer):
    kind_policies = MarathonKindPolicySerializer(many=True)


class MarathonKindPolicyWriteSerializer(serializers.Serializer):
    container_kind = serializers.ChoiceField(choices=MediaContainerKind.choices)
    min_run = serializers.IntegerField(min_value=0)
    max_run = serializers.IntegerField(min_value=0)
    quota = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        if attrs["max_run"] and attrs["min_run"] > attrs["max_run"]:
            raise serializers.ValidationError("min_run must be <= max_run.")
        return attrs


class MarathonConfigWriteSerializer(serializers.Serializer):
    kind_policies = MarathonKindPolicyWriteSerializer(many=True)

    def validate_kind_policies(self, value):
        kinds = [policy["container_kind"] for policy in value]
        if len(kinds) != len(set(kinds)):
            raise serializers.ValidationError("Each container kind may appear only once.")
        return value
