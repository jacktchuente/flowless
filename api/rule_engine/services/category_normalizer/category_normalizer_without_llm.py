from __future__ import annotations

import re
import unicodedata
from typing import Any, TypedDict

from rule_engine.models import CategoryRule as CategoryRuleModel


class RulePayload(TypedDict, total=False):
    fields: list[str]
    values: list[str]


class CategoryNormalizerWithoutLlm:
    FIELD_ALIASES = {
        "title": "title",
        "description": "description",

        "tag": "tags",
        "tags": "tags",

        "genre": "genres",
        "genres": "genres",

        "category": "categories",
        "categories": "categories",
    }

    def __init__(self, media_container):
        self.media_container = media_container

    def get_categories(self) -> list[str]:
        matched_categories: list[str] = []

        category_rules = CategoryRuleModel.objects.select_related(
            "category",
        ).all()

        for category_rule in category_rules:
            category_name = category_rule.category.category
            rules = category_rule.rules or []

            if not isinstance(rules, list):
                continue

            if self._rules_match(rules):
                matched_categories.append(category_name)

        return matched_categories

    def _rules_match(self, rules: list[dict[str, Any]]) -> bool:
        return any(
            self._rule_matches(rule)
            for rule in rules
            if isinstance(rule, dict)
        )

    def _rule_matches(self, rule: dict[str, Any]) -> bool:
        fields = rule.get("fields", [])
        values = rule.get("values", [])

        if not isinstance(fields, list) or not isinstance(values, list):
            return False

        for field in fields:
            if not isinstance(field, str):
                continue

            field_values = self._get_field_values(field)

            for field_value in field_values:
                for expected_value in values:
                    if not isinstance(expected_value, str):
                        continue

                    if self._value_matches(expected_value, field_value):
                        return True

        return False

    def _get_field_values(self, field: str) -> list[str]:
        model_field = self.FIELD_ALIASES.get(field, field)

        value = getattr(self.media_container, model_field, None)

        if value is None:
            return []

        if isinstance(value, str):
            return [value]

        if isinstance(value, list):
            return [
                item
                for item in value
                if isinstance(item, str)
            ]

        return [str(value)]

    @classmethod
    def _value_matches(
            cls,
            expected_value: str,
            candidate_value: str,
    ) -> bool:
        expected = cls._normalize_text(expected_value)
        candidate = cls._normalize_text(candidate_value)

        if not expected or not candidate:
            return False

        pattern = rf"(?<![a-z0-9]){re.escape(expected)}(?![a-z0-9])"

        return re.search(pattern, candidate) is not None

    @staticmethod
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""

        text = str(value)

        text = unicodedata.normalize("NFKD", text)
        text = "".join(
            char
            for char in text
            if not unicodedata.combining(char)
        )

        text = text.lower()
        text = re.sub(r"[^a-z0-9]+", " ", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()
