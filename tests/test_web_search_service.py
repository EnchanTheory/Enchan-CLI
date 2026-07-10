import sys
import types
import unittest

from backend import web_search_service


class FakeDDGS:
    requested_max_results = None
    results = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def text(self, query, max_results=5):
        self.__class__.requested_max_results = max_results
        return iter(self.__class__.results)


class WebSearchAdFilterTest(unittest.TestCase):
    def setUp(self):
        self.original_ddgs = sys.modules.get("ddgs")
        sys.modules["ddgs"] = types.SimpleNamespace(DDGS=FakeDDGS)
        FakeDDGS.requested_max_results = None
        FakeDDGS.results = []

    def tearDown(self):
        if self.original_ddgs is None:
            sys.modules.pop("ddgs", None)
        else:
            sys.modules["ddgs"] = self.original_ddgs

    def test_filters_ad_click_redirect_urls(self):
        FakeDDGS.results = [
            {
                "title": "Bing sponsored result",
                "href": "https://www.bing.com/aclick?ld=example",
                "body": "ad copy",
            },
            {
                "title": "Google sponsored result",
                "href": "https://www.google.com/aclk?sa=l&adurl=https://example.com",
                "body": "ad copy",
            },
            {
                "title": "Organic result",
                "href": "https://example.com/news",
                "body": "organic snippet",
            },
        ]

        results = web_search_service.perform_web_search("news", max_results=5)

        self.assertEqual(results, [
            {
                "title": "Organic result",
                "url": "https://example.com/news",
                "snippet": "organic snippet",
            }
        ])

    def test_filters_localized_ad_title_marker(self):
        self.assertTrue(web_search_service._is_ad_result({
            "title": "公式／ヴァンテージマネジメント - 広告ならヴァンテージにおまかせ - 【広告】",
            "href": "https://example.com/landing",
            "body": "手数料がずっと10％のリスティング広告。",
        }))

    def test_tops_up_after_filtering_ads(self):
        FakeDDGS.results = [
            {"title": "Ad 1", "href": "https://duckduckgo.com/y.js?ad_domain=x", "body": "ad"},
            {"title": "Organic 1", "href": "https://example.com/1", "body": "one"},
            {"title": "Ad 2", "href": "https://googleadservices.com/pagead/aclk?x=1", "body": "ad"},
            {"title": "Organic 2", "href": "https://example.com/2", "body": "two"},
            {"title": "Organic 3", "href": "https://example.com/3", "body": "three"},
        ]

        results = web_search_service.perform_web_search("news", max_results=3)

        self.assertEqual([result["title"] for result in results], ["Organic 1", "Organic 2", "Organic 3"])
        self.assertEqual(FakeDDGS.requested_max_results, 6)


if __name__ == "__main__":
    unittest.main()
