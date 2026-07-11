import unittest
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree

from app.sitemap import STATIC_PATHS, buildSitemap

SITEMAP_NAMESPACE = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class SitemapTest(unittest.TestCase):
    def testSitemapIncludesStaticPagesAndArticles(self) -> None:
        xml = buildSitemap(
            "https://jackhales.com/",
            [
                {
                    "slug": "latest-article",
                    "updatedAt": datetime(2026, 7, 11, 14, 30, tzinfo=timezone(timedelta(hours=10))),
                },
                {"slug": "older article", "updatedAt": datetime(2025, 1, 2)},
            ],
        )

        root = ElementTree.fromstring(xml)
        locations = [element.text for element in root.findall("sitemap:url/sitemap:loc", SITEMAP_NAMESPACE)]

        self.assertEqual(
            locations,
            [
                *[f"https://jackhales.com{path}" for path in STATIC_PATHS],
                "https://jackhales.com/article/latest-article",
                "https://jackhales.com/article/older%20article",
            ],
        )
        self.assertEqual(
            [element.text for element in root.findall("sitemap:url/sitemap:lastmod", SITEMAP_NAMESPACE)],
            ["2026-07-11", "2025-01-02"],
        )

    def testSitemapEscapesUrlsAndSkipsInvalidOrDuplicateArticles(self) -> None:
        xml = buildSitemap(
            "https://jackhales.com?preview=1&format=xml",
            [{"slug": "article"}, {"slug": "article"}, {"slug": ""}, {}],
        )

        root = ElementTree.fromstring(xml)
        locations = [element.text for element in root.findall("sitemap:url/sitemap:loc", SITEMAP_NAMESPACE)]

        self.assertEqual(len(locations), len(STATIC_PATHS) + 1)
        self.assertEqual(locations[0], "https://jackhales.com?preview=1&format=xml")


if __name__ == "__main__":
    unittest.main()
