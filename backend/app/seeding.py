import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


seedPath = Path(__file__).resolve().parent.parent / "seed" / "articles.json"


def loadSeedArticles(now: datetime | None = None) -> list[dict[str, Any]]:
    seededAt = now or datetime.now(UTC)
    articles = json.loads(seedPath.read_text())
    for article in articles:
        article["slug"] = article["slug"].strip().lower()
        article["publishedAt"] = datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00"))
        article["createdAt"] = seededAt
        article["updatedAt"] = seededAt
    return articles


async def seedArticles(database: Any) -> int:
    if await database.articles.estimated_document_count() > 0:
        return 0
    articles = loadSeedArticles()
    if articles:
        await database.articles.insert_many(articles)
    return len(articles)


async def reseedArticles(database: Any) -> dict[str, int]:
    articleResult = await database.articles.delete_many({})
    viewResult = await database.articleViews.delete_many({})
    sessionResult = await database.adminSessions.delete_many({})

    articles = loadSeedArticles()
    if articles:
        await database.articles.insert_many(articles)

    return {
        "articlesDeleted": articleResult.deleted_count,
        "articlesInserted": len(articles),
        "articleViewsDeleted": viewResult.deleted_count,
        "adminSessionsDeleted": sessionResult.deleted_count,
    }
