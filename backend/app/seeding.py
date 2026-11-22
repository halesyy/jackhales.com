import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

seedPath = Path(__file__).resolve().parent.parent / "seed" / "articles.json"
seedRoot = seedPath.parent.resolve()
reseedTokenPath = Path(__file__).resolve().parent.parent / "seed" / "reseed.once"


def loadSeedArticles(now: datetime | None = None) -> list[dict[str, Any]]:
    seededAt = now or datetime.now(UTC)
    articles = json.loads(seedPath.read_text())
    for article in articles:
        bodyMarkdownPath = article.pop("bodyMarkdownPath", None)
        if bodyMarkdownPath:
            resolvedBodyPath = (seedRoot / bodyMarkdownPath).resolve()
            try:
                resolvedBodyPath.relative_to(seedRoot)
            except ValueError as error:
                raise ValueError(f"Article body path escapes seed directory: {bodyMarkdownPath}") from error
            article["bodyMarkdown"] = resolvedBodyPath.read_text().strip()
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


async def syncVersionedSeedArticles(database: Any) -> int:
    synced = 0
    for article in loadSeedArticles():
        seedVersion = article.get("seedVersion")
        if not seedVersion:
            continue

        slug = article["slug"]
        operationId = f"article:{slug}:{seedVersion}"
        completedRun = await database.maintenanceRuns.find_one({"_id": operationId, "status": "completed"})
        if completedRun:
            continue

        existing = await database.articles.find_one({"slug": slug})
        action = "current"
        if existing and existing.get("seedVersion") != seedVersion:
            existingBackup = await database.maintenanceBackups.find_one({"_id": operationId}, {"_id": 1})
            if existingBackup is None:
                await database.maintenanceBackups.insert_one(
                    {
                        "_id": operationId,
                        "createdAt": datetime.now(UTC),
                        "collections": {"articles": [existing]},
                    }
                )

            update = {key: value for key, value in article.items() if key != "createdAt"}
            await database.articles.update_one({"_id": existing["_id"]}, {"$set": update})
            action = "updated"
            synced += 1
        elif existing is None:
            await database.articles.insert_one(article)
            action = "inserted"
            synced += 1

        await database.maintenanceRuns.update_one(
            {"_id": operationId},
            {
                "$setOnInsert": {"startedAt": datetime.now(UTC)},
                "$set": {
                    "status": "completed",
                    "completedAt": datetime.now(UTC),
                    "summary": {"action": action, "slug": slug, "seedVersion": seedVersion},
                },
            },
            upsert=True,
        )

    return synced


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


def loadReseedToken(path: Path = reseedTokenPath) -> str | None:
    if not path.exists():
        return None
    token = path.read_text().strip()
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", token):
        raise ValueError("Invalid reseed token")
    return token


async def backupCollections(database: Any) -> dict[str, list[dict[str, Any]]]:
    backup: dict[str, list[dict[str, Any]]] = {}
    for collectionName in ("articles", "articleViews", "adminSessions"):
        collection = database[collectionName]
        backup[collectionName] = [document async for document in collection.find({})]
    return backup


async def applyPendingReseed(database: Any) -> dict[str, int] | None:
    token = loadReseedToken()
    if token is None:
        return None

    operationId = f"articles:{token}"
    completedRun = await database.maintenanceRuns.find_one({"_id": operationId, "status": "completed"})
    if completedRun:
        return completedRun.get("summary")

    existingBackup = await database.maintenanceBackups.find_one({"_id": operationId}, {"_id": 1})
    if existingBackup is None:
        await database.maintenanceBackups.insert_one(
            {
                "_id": operationId,
                "createdAt": datetime.now(UTC),
                "collections": await backupCollections(database),
            }
        )

    await database.maintenanceRuns.update_one(
        {"_id": operationId},
        {"$setOnInsert": {"startedAt": datetime.now(UTC)}, "$set": {"status": "running"}},
        upsert=True,
    )
    summary = await reseedArticles(database)
    await database.maintenanceRuns.update_one(
        {"_id": operationId},
        {"$set": {"status": "completed", "completedAt": datetime.now(UTC), "summary": summary}},
    )
    return summary
