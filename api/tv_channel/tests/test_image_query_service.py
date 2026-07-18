from unittest.mock import patch

from django.test import TestCase

from tv_channel.models import Catalog, EditorialLine, TvChannel
from tv_channel.services.image_suggestion.query_service import (
    ChannelImageQueryService,
    ImageQueryError,
)
from utils.llm_service import LLMResponse

LLM_PATCH = "tv_channel.services.image_suggestion.query_service.LLMService"


class ChannelImageQueryServiceTests(TestCase):
    def setUp(self):
        self.catalog = Catalog.objects.create(name="Query catalog")
        self.channel = TvChannel.objects.create(
            name="Ghibli TV",
            description="Animation marathon channel",
            catalog=self.catalog,
        )

    def _set_editorial_line(self, *, preferred=None, allowed=None):
        EditorialLine.objects.update_or_create(
            tv_channel=self.channel,
            defaults={"preferred": preferred or {}, "allowed": allowed or {}},
        )
        self.channel.refresh_from_db()

    def test_preferred_studio_axis_resolves_without_llm(self):
        self._set_editorial_line(preferred={"studios": ["Studio Ghibli"]})
        with patch(LLM_PATCH) as llm_mock:
            query = ChannelImageQueryService(self.channel).resolve()
        llm_mock.assert_not_called()
        self.assertEqual((query.entity_type, query.query, query.source), ("studio", "Studio Ghibli", "axes"))

    def test_allowed_actor_axis_used_when_no_studio(self):
        self._set_editorial_line(allowed={"actors": ["Toshiro Mifune", "Other"]})
        query = ChannelImageQueryService(self.channel).resolve()
        self.assertEqual((query.entity_type, query.query, query.source), ("person", "Toshiro Mifune", "axes"))

    def test_studio_axis_wins_over_actor_axis(self):
        self._set_editorial_line(
            preferred={"actors": ["Someone"]},
            allowed={"studios": ["A24"]},
        )
        query = ChannelImageQueryService(self.channel).resolve()
        self.assertEqual((query.entity_type, query.query), ("studio", "A24"))

    def test_user_override_wins_over_axes(self):
        self._set_editorial_line(preferred={"studios": ["Studio Ghibli"]})
        query = ChannelImageQueryService(self.channel).resolve(query="Akira", entity_type="theme")
        self.assertEqual((query.entity_type, query.query, query.source), ("theme", "Akira", "user"))

    def test_user_override_defaults_unknown_entity_type_to_theme(self):
        query = ChannelImageQueryService(self.channel).resolve(query="noir", entity_type="bogus")
        self.assertEqual((query.entity_type, query.source), ("theme", "user"))

    def test_llm_fallback_parses_tagged_json(self):
        self._set_editorial_line()
        content = 'blah <image_query>{"entity_type": "person", "query": "Hayao Miyazaki"}</image_query>'
        with patch(LLM_PATCH) as llm_mock:
            llm_mock.return_value.complete.return_value = LLMResponse(content=content, raw_response=None)
            query = ChannelImageQueryService(self.channel).resolve()
        self.assertEqual((query.entity_type, query.query, query.source), ("person", "Hayao Miyazaki", "llm"))

    def test_llm_fallback_retries_then_succeeds(self):
        self._set_editorial_line()
        bad = LLMResponse(content="no tags here", raw_response=None)
        good = LLMResponse(
            content='<image_query>{"entity_type": "theme", "query": "space opera"}</image_query>',
            raw_response=None,
        )
        with patch(LLM_PATCH) as llm_mock:
            llm_mock.return_value.complete.side_effect = [bad, good]
            query = ChannelImageQueryService(self.channel).resolve()
        self.assertEqual(query.query, "space opera")
        self.assertEqual(llm_mock.return_value.complete.call_count, 2)

    def test_llm_fallback_fails_after_retries(self):
        self._set_editorial_line()
        bad = LLMResponse(content='<image_query>{"entity_type": "nope", "query": "x"}</image_query>', raw_response=None)
        with patch(LLM_PATCH) as llm_mock, self.settings(LLM_RETRY_IMAGE_QUERY=2):
            llm_mock.return_value.complete.return_value = bad
            with self.assertRaises(ImageQueryError):
                ChannelImageQueryService(self.channel).resolve()
        self.assertEqual(llm_mock.return_value.complete.call_count, 2)

    def test_resolve_from_axes_returns_none_without_line_or_axes(self):
        self.assertIsNone(ChannelImageQueryService(self.channel).resolve_from_axes())
        self._set_editorial_line(preferred={"categories": ["anime"]})
        self.assertIsNone(ChannelImageQueryService(self.channel).resolve_from_axes())
