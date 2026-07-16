from rest_framework.test import APITestCase

from rule_engine.models import VocabularyEntry


class RuleOptionSearchApiTests(APITestCase):

    URL = "/api/tv-channel/rule-option-search/"

    def setUp(self):
        VocabularyEntry.objects.bulk_create([
            VocabularyEntry(axis="actors", value="Tom Hanks"),
            VocabularyEntry(axis="actors", value="Tommy Lee Jones"),
            VocabularyEntry(axis="directors", value="Tom Hooper"),
            VocabularyEntry(axis="studios", value="Warner Bros."),
        ])

    def test_short_query_returns_empty(self):
        response = self.client.get(self.URL, {"q": "t"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"results": []})

    def test_search_is_multiplexed_across_axes(self):
        response = self.client.get(self.URL, {"q": "tom"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["results"],
            [
                {"axis": "actors", "value": "Tom Hanks"},
                {"axis": "actors", "value": "Tommy Lee Jones"},
                {"axis": "directors", "value": "Tom Hooper"},
            ],
        )

    def test_limit_is_applied_and_capped(self):
        response = self.client.get(self.URL, {"q": "tom", "limit": 2})
        self.assertEqual(len(response.data["results"]), 2)

        response = self.client.get(self.URL, {"q": "tom", "limit": "abc"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 3)
