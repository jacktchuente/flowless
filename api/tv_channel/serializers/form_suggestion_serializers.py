from rest_framework import serializers


class FormSuggestionRequestSerializer(serializers.Serializer):
    form_kind = serializers.ChoiceField(choices=("editorial_line", "grid_block", "grid"))
    user_context = serializers.CharField(required=False, allow_blank=True, default="")
    current_values = serializers.DictField(required=False, default=dict)
    grid_block_id = serializers.IntegerField(required=False)
