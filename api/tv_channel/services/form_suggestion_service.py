from __future__ import annotations

import json
import re

from django.conf import settings
from rest_framework.serializers import ValidationError

from media_source.constants import MediaContainerKind, MediaNature
from rule_engine.services import category_service
from tv_channel.models import FillerPolicy
from tv_channel.serializers.editorial_line_serializers import EditorialLineWriteSerializer
from tv_channel.serializers.grid_block_serializers import GridBlockWriteSerializer
from tv_channel.serializers.grid_serializers import GridWriteSerializer
from utils.format_with_jinja import format_with_jinja
from utils.llm_service import LLMService


class FormSuggestionError(ValueError):
    pass


class FormSuggestionService:
    FORM_SERIALIZERS = {
        "editorial_line": EditorialLineWriteSerializer,
        "grid_block": GridBlockWriteSerializer,
        "grid": GridWriteSerializer,
    }

    def __init__(self, tv_channel, form_kind, user_context, current_values, grid_block=None):
        if form_kind not in self.FORM_SERIALIZERS:
            raise FormSuggestionError(f"Unsupported form kind: {form_kind}.")
        self.tv_channel = tv_channel
        self.form_kind = form_kind
        self.user_context = user_context
        self.current_values = current_values
        self.grid_block = grid_block

    def suggest(self) -> dict:
        retry_errors = []
        attempts = max(1, int(getattr(settings, "LLM_RETRY_FORM_SUGGESTION", 3)))
        last_error = "Form suggestion failed."
        for _ in range(attempts):
            try:
                response = LLMService().complete(prompt=self._build_prompt(retry_errors))
                payload = self._parse(response.content)
                serializer = self.FORM_SERIALIZERS[self.form_kind](data=payload, partial=True)
                serializer.is_valid(raise_exception=True)
                return self._serialize_values(serializer.validated_data)
            except (FormSuggestionError, ValidationError) as exc:
                last_error = str(exc.detail if isinstance(exc, ValidationError) else exc)
                retry_errors = [last_error]
            except Exception as exc:
                last_error = f"LLM request failed: {exc}"
                retry_errors = [last_error]
        raise FormSuggestionError(last_error)

    def _build_prompt(self, retry_errors):
        active_grid = self.tv_channel.gridlayout_set.filter(is_active=True).first()
        editorial = getattr(self.tv_channel, "editorialline", None)
        blocks = []
        if active_grid is not None:
            blocks = list(active_grid.gridblock_set.order_by("starts_at").values(
                "id", "starts_at", "ends_at", "allowed_categories", "forbidden_categories",
                "allowed_natures", "forbidden_natures", "allowed_container_kinds", "forbidden_container_kinds",
            ))
        context = {
            "channel": {"name": self.tv_channel.name, "description": self.tv_channel.description or "", "specification": self.tv_channel.specification or ""},
            "catalog": {"name": self.tv_channel.catalog.name, "description": self.tv_channel.catalog.description or ""},
            "grid_mode": active_grid.get_mode_display() if active_grid else "unknown",
            "editorial_line": self._model_values(editorial),
            "blocks": self._json_safe(blocks),
            "current_block_id": self.grid_block.pk if self.grid_block else None,
            "categories": category_service.get_all_category_names(),
            "natures": [choice.label for choice in MediaNature],
            "container_kinds": [choice.label for choice in MediaContainerKind],
            "filler_policies": list(FillerPolicy.objects.order_by("name").values("id", "name", "duration_seconds")),
            "current_values": self._json_safe(self.current_values),
            "user_context": self.user_context,
            "retry_errors": retry_errors,
        }
        path = settings.BASE_DIR / "templates" / "tv_channel" / "prompts" / f"form_suggestion_{self.form_kind}_prompt.j2"
        return format_with_jinja(path, context)

    @staticmethod
    def _model_values(instance):
        if instance is None:
            return None
        return FormSuggestionService._json_safe({
            field.name: getattr(instance, field.name)
            for field in instance._meta.fields if field.name not in ("id", "tv_channel")
        })

    @staticmethod
    def _json_safe(value):
        if isinstance(value, dict):
            return {key: FormSuggestionService._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [FormSuggestionService._json_safe(item) for item in value]
        if hasattr(value, "isoformat"):
            return value.isoformat()
        if hasattr(value, "pk"):
            return value.pk
        return value

    @staticmethod
    def _parse(content):
        if not content or not content.strip():
            raise FormSuggestionError("LLM returned an empty response.")
        match = re.search(r"<suggestion_output>\s*(\{.*?\})\s*</suggestion_output>", content, re.DOTALL)
        if not match:
            raise FormSuggestionError("LLM response is missing suggestion_output tags.")
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            raise FormSuggestionError("LLM returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise FormSuggestionError("LLM returned an invalid top-level payload.")
        return payload

    @staticmethod
    def _serialize_values(values):
        result = {}
        for key, value in values.items():
            if hasattr(value, "isoformat"):
                result[key] = value.strftime("%H:%M") if hasattr(value, "hour") else value.isoformat()
            elif hasattr(value, "pk"):
                result[key] = value.pk
            else:
                result[key] = value
        return result
