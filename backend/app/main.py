import re
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError, PyMongoError

from .auth_migration import applyPendingAuthMigration
from .config import getSettings
from .database import closeClient, ensureIndexes, getDatabase
from .schemas import AdminCredentials, ArticleCreate, ArticleOut, ArticleSummary, ArticleUpdate
from .security import (
    adminEmail,
    authenticatedAdminEmail,
    createSession,
    getClientIp,
    hashPassword,
    requireAdmin,
    tokenHash,
    verifyPassword,
    viewIpHash,
)
from .seeding import applyPendingReseed, seedArticles
from .sitemap import buildSitemap


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "untitled"


def serializeArticle(document: dict) -> dict:
    return {
        "id": str(document["_id"]),
        "title": document["title"],
        "slug": document["slug"],
        "summary": document.get("summary", ""),
        "bodyMarkdown": document.get("bodyMarkdown", ""),
        "publishedAt": document["publishedAt"],
        "status": document.get("status", "draft"),
        "sourceUrl": document.get("sourceUrl"),
        "createdAt": document["createdAt"],
        "updatedAt": document["updatedAt"],
    }


def serializeSummary(document: dict) -> dict:
    article = serializeArticle(document)
    article.pop("bodyMarkdown", None)
    article.pop("sourceUrl", None)
    article.pop("createdAt", None)
    return article


@asynccontextmanager
async def lifespan(app: FastAPI):
    await applyPendingReseed(getDatabase())
    await applyPendingAuthMigration(getDatabase())
    await ensureIndexes()
    await seedArticles(getDatabase())
    yield
    await closeClient()


app = FastAPI(title="Jack Hales Blog API", lifespan=lifespan)
settings = getSettings()
corsOrigins = settings["corsOrigins"]
if corsOrigins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(corsOrigins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def database() -> AsyncIOMotorDatabase:
    return getDatabase()


async def adminOnly(request: Request, database: AsyncIOMotorDatabase = Depends(database)) -> None:
    await requireAdmin(database, request)


def setAdminSessionCookie(response: Response, token: str) -> None:
    response.set_cookie(
        "adminSession",
        token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        path="/",
    )


@app.get("/api/health")
async def health(database: AsyncIOMotorDatabase = Depends(database)) -> dict[str, str]:
    try:
        await database.command("ping")
    except PyMongoError as error:
        raise HTTPException(status_code=503, detail="database unavailable") from error
    return {"status": "ok", "database": "ok"}


@app.get("/api/articles", response_model=list[ArticleSummary])
async def listArticles(database: AsyncIOMotorDatabase = Depends(database)) -> list[dict]:
    cursor = database.articles.find({"status": "published"}).sort("publishedAt", -1)
    return [serializeSummary(article) async for article in cursor]


@app.get("/api/articles/{slug}", response_model=ArticleOut)
async def getArticle(slug: str, database: AsyncIOMotorDatabase = Depends(database)) -> dict:
    article = await database.articles.find_one({"slug": slug, "status": "published"})
    if not article:
        raise HTTPException(status_code=404, detail="article not found")
    return serializeArticle(article)


@app.get("/api/articles/{slug}/views")
async def getArticleViews(slug: str, database: AsyncIOMotorDatabase = Depends(database)) -> dict[str, int]:
    article = await database.articles.find_one({"slug": slug, "status": "published"}, {"_id": 1})
    if not article:
        raise HTTPException(status_code=404, detail="article not found")
    return {"views": await database.articleViews.count_documents({"articleSlug": slug})}


@app.post("/api/articles/{slug}/views")
async def recordArticleView(request: Request, slug: str, database: AsyncIOMotorDatabase = Depends(database)) -> dict[str, int | bool]:
    article = await database.articles.find_one({"slug": slug, "status": "published"}, {"_id": 1})
    if not article:
        raise HTTPException(status_code=404, detail="article not found")

    now = datetime.now(UTC)
    hourBucket = now.replace(minute=0, second=0, microsecond=0)
    viewKey = {
        "articleSlug": slug,
        "ipHash": viewIpHash(getClientIp(request)),
        "hourBucket": hourBucket,
    }
    counted = False
    try:
        result = await database.articleViews.update_one(
            viewKey,
            {"$setOnInsert": {**viewKey, "createdAt": now}},
            upsert=True,
        )
        counted = result.upserted_id is not None
    except DuplicateKeyError:
        # Concurrent requests for the same visitor/hour resolve to one view.
        counted = False

    views = await database.articleViews.count_documents({"articleSlug": slug})
    return {"views": views, "counted": counted}


@app.get("/api/sitemap", response_class=Response)
async def sitemap(database: AsyncIOMotorDatabase = Depends(database)) -> Response:
    cursor = database.articles.find({"status": "published"}, {"slug": 1, "updatedAt": 1}).sort("publishedAt", -1)
    articles = [article async for article in cursor]
    return Response(
        content=buildSitemap(str(settings["publicSiteUrl"]), articles),
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=300"},
    )


@app.get("/api/admin/status")
async def adminStatus(request: Request, database: AsyncIOMotorDatabase = Depends(database)) -> dict[str, bool | str]:
    admin = await database.adminUsers.find_one({"_id": adminEmail, "email": adminEmail, "role": "admin"}, {"_id": 1})
    authenticated = await authenticatedAdminEmail(database, request)
    return {"configured": bool(admin), "authenticated": authenticated == adminEmail, "email": adminEmail}


@app.post("/api/admin/bootstrap")
async def bootstrapAdmin(
    payload: AdminCredentials,
    response: Response,
    database: AsyncIOMotorDatabase = Depends(database),
) -> dict[str, bool]:
    if payload.email != adminEmail:
        raise HTTPException(status_code=403, detail=f"admin must use {adminEmail}")
    if await database.adminUsers.count_documents({}) > 0:
        raise HTTPException(status_code=409, detail="admin account already exists")

    now = datetime.now(UTC)
    try:
        await database.adminUsers.insert_one(
            {
                "_id": adminEmail,
                "email": adminEmail,
                "passwordHash": hashPassword(payload.password),
                "role": "admin",
                "createdAt": now,
                "updatedAt": now,
            }
        )
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail="admin account already exists") from error

    await database.adminSessions.delete_many({})
    token = await createSession(database, adminEmail)
    setAdminSessionCookie(response, token)
    return {"ok": True}


@app.post("/api/admin/login")
async def loginAdmin(
    payload: AdminCredentials,
    response: Response,
    database: AsyncIOMotorDatabase = Depends(database),
) -> dict[str, bool]:
    admin = await database.adminUsers.find_one({"_id": adminEmail, "email": adminEmail, "role": "admin"})
    storedHash = str(admin.get("passwordHash", "")) if admin else ""
    passwordMatches = verifyPassword(payload.password, storedHash)
    if payload.email != adminEmail or not admin or not passwordMatches:
        raise HTTPException(status_code=401, detail="invalid email or password")

    token = await createSession(database, adminEmail)
    setAdminSessionCookie(response, token)
    return {"ok": True}


@app.post("/api/admin/logout")
async def logoutAdmin(request: Request, response: Response, database: AsyncIOMotorDatabase = Depends(database)) -> dict[str, bool]:
    token = request.cookies.get("adminSession")
    if token:
        await database.adminSessions.delete_one({"tokenHash": tokenHash(token)})
    response.delete_cookie("adminSession", path="/", secure=True, httponly=True, samesite="lax")
    return {"ok": True}


@app.get("/api/admin/articles", response_model=list[ArticleSummary], dependencies=[Depends(adminOnly)])
async def adminListArticles(database: AsyncIOMotorDatabase = Depends(database)) -> list[dict]:
    cursor = database.articles.find({}).sort("publishedAt", -1)
    return [serializeSummary(article) async for article in cursor]


@app.get("/api/admin/articles/{slug}", response_model=ArticleOut, dependencies=[Depends(adminOnly)])
async def adminGetArticle(slug: str, database: AsyncIOMotorDatabase = Depends(database)) -> dict:
    article = await database.articles.find_one({"slug": slug})
    if not article:
        raise HTTPException(status_code=404, detail="article not found")
    return serializeArticle(article)


@app.post("/api/admin/articles", response_model=ArticleOut, dependencies=[Depends(adminOnly)])
async def createArticle(payload: ArticleCreate, database: AsyncIOMotorDatabase = Depends(database)) -> dict:
    now = datetime.now(UTC)
    document = payload.model_dump()
    document["slug"] = slugify(document["slug"])
    document["createdAt"] = now
    document["updatedAt"] = now
    result = await database.articles.insert_one(document)
    created = await database.articles.find_one({"_id": result.inserted_id})
    return serializeArticle(created)


@app.put("/api/admin/articles/{slug}", response_model=ArticleOut, dependencies=[Depends(adminOnly)])
async def updateArticle(slug: str, payload: ArticleUpdate, database: AsyncIOMotorDatabase = Depends(database)) -> dict:
    existing = await database.articles.find_one({"slug": slug})
    if not existing:
        raise HTTPException(status_code=404, detail="article not found")
    update = {key: value for key, value in payload.model_dump(exclude_unset=True).items() if value is not None}
    if "slug" in update:
        update["slug"] = slugify(update["slug"])
    update["updatedAt"] = datetime.now(UTC)
    await database.articles.update_one({"_id": existing["_id"]}, {"$set": update})
    updatedSlug = update.get("slug", slug)
    if updatedSlug != slug:
        await database.articleViews.update_many({"articleSlug": slug}, {"$set": {"articleSlug": updatedSlug}})
    article = await database.articles.find_one({"slug": updatedSlug})
    return serializeArticle(article)
