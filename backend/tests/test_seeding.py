import unittest
from datetime import UTC, datetime

from app.seeding import loadSeedArticles, reseedArticles


class FakeDeleteResult:
    def __init__(self, deletedCount: int) -> None:
        self.deleted_count = deletedCount


class FakeCollection:
    def __init__(self, deletedCount: int = 0) -> None:
        self.deletedCount = deletedCount
        self.insertedDocuments: list[dict] = []

    async def delete_many(self, query: dict) -> FakeDeleteResult:
        self.assertEmptyQuery(query)
        return FakeDeleteResult(self.deletedCount)

    async def insert_many(self, documents: list[dict]) -> None:
        self.insertedDocuments = documents

    @staticmethod
    def assertEmptyQuery(query: dict) -> None:
        if query:
            raise AssertionError(f"Expected an empty collection query, received {query}")


class FakeDatabase:
    def __init__(self) -> None:
        self.articles = FakeCollection(13)
        self.articleViews = FakeCollection(4)
        self.adminSessions = FakeCollection(2)


class SeedArticlesTest(unittest.TestCase):
    def testSeedArticlesAreCanonicalAndDeterministic(self) -> None:
        seededAt = datetime(2026, 7, 11, tzinfo=UTC)
        articles = loadSeedArticles(seededAt)

        self.assertEqual(len(articles), 10)
        self.assertEqual(len({article["slug"] for article in articles}), 10)
        self.assertNotIn("test", {article["slug"] for article in articles})
        self.assertTrue(all(article["createdAt"] == seededAt for article in articles))
        self.assertTrue(all(article["updatedAt"] == seededAt for article in articles))
        self.assertTrue(all(article["publishedAt"].tzinfo is not None for article in articles))


class ReseedArticlesTest(unittest.IsolatedAsyncioTestCase):
    async def testReseedReplacesArticlesAndClearsTransientCollections(self) -> None:
        database = FakeDatabase()

        summary = await reseedArticles(database)

        self.assertEqual(
            summary,
            {
                "articlesDeleted": 13,
                "articlesInserted": 10,
                "articleViewsDeleted": 4,
                "adminSessionsDeleted": 2,
            },
        )
        self.assertEqual(len(database.articles.insertedDocuments), 10)


if __name__ == "__main__":
    unittest.main()
