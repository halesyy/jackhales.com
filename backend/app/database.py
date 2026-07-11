from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import getSettings

client: AsyncIOMotorClient | None = None


def getClient() -> AsyncIOMotorClient:
    global client
    if client is None:
        settings = getSettings()
        client = AsyncIOMotorClient(str(settings["mongodbUrl"]))
    return client


def getDatabase() -> AsyncIOMotorDatabase:
    settings = getSettings()
    return getClient()[str(settings["mongodbDatabase"])]


async def ensureIndexes() -> None:
    database = getDatabase()
    await database.articles.create_index("slug", unique=True)
    await database.articles.create_index([("status", 1), ("publishedAt", -1)])
    await database.articleViews.create_index(
        [("articleSlug", 1), ("ipHash", 1), ("hourBucket", 1)],
        unique=True,
        name="unique_article_ip_hour",
    )
    await database.adminSessions.create_index("tokenHash", unique=True)
    await database.adminSessions.create_index("expiresAt", expireAfterSeconds=0)
    await database.adminUsers.create_index("email", unique=True)


async def closeClient() -> None:
    global client
    if client is not None:
        client.close()
        client = None
