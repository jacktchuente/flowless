from unittest.mock import patch

from django.test import TestCase

from media_source.models import MediaCollection, MediaContainer, MediaSource
from media_source.constants import MediaContainerKind
from project_ops.constants import AnalyzeStatus
from tv_channel.models import Catalog, EditorialLine, TvChannel
from tv_channel.services.image_suggestion.providers.base import ImageResult, ImageSearchProvider
from tv_channel.services.image_suggestion.providers.jellyfin_provider import JellyfinImageProvider
from tv_channel.services.image_suggestion.providers.tmdb_provider import TmdbImageProvider
from tv_channel.services.image_suggestion.query_service import ImageQuery
from tv_channel.services.image_suggestion.search import collect_image_results

AUTH_PATCH = (
    "media_source.services.media_server_services.jellyfin_service.JellyfinService._authenticate"
)
REQUEST_PATCH = (
    "media_source.services.media_server_services.jellyfin_service.JellyfinService._request"
)


class ImageProviderFixtureMixin:
    def build_fixtures(self):
        self.catalog = Catalog.objects.create(name="Images catalog")
        self.channel = TvChannel.objects.create(name="Images channel", catalog=self.catalog)
        EditorialLine.objects.create(tv_channel=self.channel)
        self.channel.refresh_from_db()
        self.media_source = MediaSource.objects.create(
            name="jellyfin",
            is_active=True,
            credentials={"application_url": "http://jf:8096/", "username": "u", "password": "p"},
        )


class JellyfinImageProviderTests(ImageProviderFixtureMixin, TestCase):
    def setUp(self):
        self.build_fixtures()

    def test_unavailable_without_active_media_source(self):
        self.media_source.is_active = False
        self.media_source.save(update_fields=["is_active"])
        provider = JellyfinImageProvider(self.channel)
        self.assertFalse(provider.is_available())

    @patch(REQUEST_PATCH)
    @patch(AUTH_PATCH, return_value=("tok", "uid"))
    def test_studio_query_mixes_entity_primary_and_backdrops(self, _auth, request_mock):
        def fake_request(token, path, params, **kwargs):
            if path == "/Studios":
                self.assertEqual(params["searchTerm"], "Studio Ghibli")
                return {"Items": [
                    {"Id": "st1", "Name": "Studio Ghibli", "ImageTags": {"Primary": "x"}},
                ]}
            if path == "/Items":
                self.assertEqual(params["studioIds"], "st1")
                return {"Items": [
                    {"Id": "m1", "Name": "Totoro", "BackdropImageTags": ["a"]},
                    {"Id": "m2", "Name": "No backdrop", "BackdropImageTags": []},
                    {"Id": "m3", "Name": "Mononoke", "BackdropImageTags": ["b"]},
                ]}
            raise AssertionError(path)

        request_mock.side_effect = fake_request
        provider = JellyfinImageProvider(self.channel)
        results = provider.search(ImageQuery("studio", "Studio Ghibli", "axes"), limit=5)

        self.assertEqual(
            [result.source_url for result in results],
            [
                "http://jf:8096/Items/st1/Images/Primary",
                "http://jf:8096/Items/m1/Images/Backdrop/0",
                "http://jf:8096/Items/m3/Images/Backdrop/0",
            ],
        )
        self.assertTrue(all("fillWidth=400" in result.thumbnail_url for result in results))
        self.assertNotIn("tok", results[0].source_url)
        self.assertEqual(results[1].attribution, "Totoro")

    @patch(REQUEST_PATCH)
    @patch(AUTH_PATCH, return_value=("tok", "uid"))
    def test_item_images_prefer_logo_then_thumb_then_backdrop(self, _auth, request_mock):
        def fake_request(token, path, params, **kwargs):
            if path == "/Studios":
                return {"Items": [{"Id": "st1", "Name": "Ghibli", "ImageTags": {}}]}
            if path == "/Items":
                self.assertIn("ImageTags", params["fields"])
                return {"Items": [
                    {"Id": "m1", "Name": "Backdrop only", "BackdropImageTags": ["a"], "ImageTags": {}},
                    {"Id": "m2", "Name": "With thumb", "BackdropImageTags": ["a"], "ImageTags": {"Thumb": "t"}},
                    {"Id": "m3", "Name": "With logo", "BackdropImageTags": ["a"], "ImageTags": {"Logo": "l", "Thumb": "t"}},
                    {"Id": "m4", "Name": "No image", "BackdropImageTags": [], "ImageTags": {}},
                ]}
            raise AssertionError(path)

        request_mock.side_effect = fake_request
        results = JellyfinImageProvider(self.channel).search(ImageQuery("studio", "Ghibli", "axes"), limit=5)

        self.assertEqual(
            [result.source_url for result in results],
            [
                "http://jf:8096/Items/m3/Images/Logo",
                "http://jf:8096/Items/m2/Images/Thumb",
                "http://jf:8096/Items/m1/Images/Backdrop/0",
            ],
        )

    @patch(REQUEST_PATCH)
    @patch(AUTH_PATCH, return_value=("tok", "uid"))
    def test_person_query_uses_persons_endpoint(self, _auth, request_mock):
        def fake_request(token, path, params, **kwargs):
            if path == "/Persons":
                return {"Items": [{"Id": "p1", "Name": "Mifune", "ImageTags": {"Primary": "x"}}]}
            if path == "/Items":
                self.assertEqual(params["personIds"], "p1")
                return {"Items": []}
            raise AssertionError(path)

        request_mock.side_effect = fake_request
        results = JellyfinImageProvider(self.channel).search(ImageQuery("person", "Mifune", "axes"), limit=5)
        self.assertEqual(results[0].source_url, "http://jf:8096/Items/p1/Images/Primary")

    @patch(REQUEST_PATCH)
    @patch(AUTH_PATCH, return_value=("tok", "uid"))
    def test_theme_query_uses_matching_containers(self, _auth, request_mock):
        collection = MediaCollection.objects.create(
            name="Movies",
            external_id="col",
            media_source=self.media_source,
            is_active=True,
            container_kind=MediaContainerKind.STANDALONE_VIDEO,
            hash_data="x",
        )
        for index in range(2):
            MediaContainer.objects.create(
                original_data_hash=f"h{index}",
                external_id=f"jf-{index}",
                title=f"Movie {index}",
                media_source=self.media_source,
                media_collection=collection,
                analyze_status=AnalyzeStatus.COMPLETE,
            )

        def fake_request(token, path, params, **kwargs):
            self.assertEqual(path, "/Items")
            self.assertEqual(set(params["ids"].split(",")), {"jf-0", "jf-1"})
            return {"Items": [{"Id": "jf-1", "Name": "Movie 1", "BackdropImageTags": ["a"]}]}

        request_mock.side_effect = fake_request
        results = JellyfinImageProvider(self.channel).search(ImageQuery("theme", "anything", "llm"), limit=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source_url, "http://jf:8096/Items/jf-1/Images/Backdrop/0")


class TmdbImageProviderTests(ImageProviderFixtureMixin, TestCase):
    def setUp(self):
        self.build_fixtures()

    def test_unavailable_without_api_key(self):
        with self.settings(TMDB_API_KEY=None):
            self.assertFalse(TmdbImageProvider(self.channel).is_available())

    def test_studio_query_returns_company_logos_then_backdrops(self):
        payloads = {
            "/search/company": {"results": [{"id": 42, "name": "Ghibli"}]},
            "/company/42/images": {"logos": [{"file_path": "/logo.png", "width": 500, "height": 200}]},
            "/discover/movie": {"results": [{"title": "Totoro", "backdrop_path": "/back.jpg"}]},
        }

        def fake_get(url, params=None, timeout=None):
            class FakeResponse:
                def __init__(self, payload):
                    self._payload = payload

                def raise_for_status(self):
                    pass

                def json(self):
                    return self._payload

            self.assertEqual(params.get("api_key"), "key")
            for path, payload in payloads.items():
                if url.endswith(path):
                    return FakeResponse(payload)
            raise AssertionError(url)

        with self.settings(TMDB_API_KEY="key"):
            with patch(
                "tv_channel.services.image_suggestion.providers.tmdb_provider.requests.get",
                side_effect=fake_get,
            ):
                results = TmdbImageProvider(self.channel).search(ImageQuery("studio", "Ghibli", "axes"), limit=5)

        self.assertEqual(
            [result.source_url for result in results],
            [
                "https://image.tmdb.org/t/p/original/logo.png",
                "https://image.tmdb.org/t/p/original/back.jpg",
            ],
        )
        self.assertEqual(results[0].width, 500)
        self.assertEqual(results[0].thumbnail_url, "https://image.tmdb.org/t/p/w342/logo.png")


class _FakeProvider(ImageSearchProvider):
    name = "fake"
    available = True
    results: list[ImageResult] = []

    def is_available(self):
        return self.available

    def search(self, query, limit):
        return self.results[:limit]


class CollectImageResultsTests(ImageProviderFixtureMixin, TestCase):
    def setUp(self):
        self.build_fixtures()

    def _result(self, provider, url):
        return ImageResult(provider=provider, source_url=url, thumbnail_url=url)

    def test_second_provider_tops_up_and_duplicates_are_skipped(self):
        class ProviderA(_FakeProvider):
            name = "a"
            results = [self._result("a", "http://x/1"), self._result("a", "http://x/2")]

        class ProviderB(_FakeProvider):
            name = "b"
            results = [
                self._result("b", "http://x/2"),
                self._result("b", "http://x/3"),
                self._result("b", "http://x/4"),
                self._result("b", "http://x/5"),
                self._result("b", "http://x/6"),
            ]

        with patch("tv_channel.services.image_suggestion.providers.PROVIDERS", (ProviderA, ProviderB)):
            results, warnings = collect_image_results(
                self.channel, ImageQuery("theme", "q", "user"), limit=5
            )
        self.assertEqual(
            [result.source_url for result in results],
            ["http://x/1", "http://x/2", "http://x/3", "http://x/4", "http://x/5"],
        )
        self.assertEqual(warnings, [])

    def test_unavailable_and_failing_providers_produce_warnings(self):
        class Unavailable(_FakeProvider):
            name = "off"
            available = False

        class Failing(_FakeProvider):
            name = "broken"

            def search(self, query, limit):
                raise RuntimeError("boom")

        class Working(_FakeProvider):
            name = "ok"
            results = [self._result("ok", "http://x/1")]

        with patch(
            "tv_channel.services.image_suggestion.providers.PROVIDERS",
            (Unavailable, Failing, Working),
        ):
            results, warnings = collect_image_results(
                self.channel, ImageQuery("theme", "q", "user"), limit=5
            )
        self.assertEqual(len(results), 1)
        self.assertEqual(len(warnings), 2)
        self.assertIn("off", warnings[0])
        self.assertIn("broken", warnings[1])
