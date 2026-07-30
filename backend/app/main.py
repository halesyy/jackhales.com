import re
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError, PyMongoError

from .apikeys import (
    getApiKeyRecord,
    issueApiKey,
    revokeApiKey,
    serializeApiKey,
)
from .apikeys import (
    requireApiKey as requireApiKeyRecord,
)
from .auth_migration import applyPendingAuthMigration
from .config import getSettings
from .content import (
    ContentEditError,
    deleteSection,
    insertSection,
    replaceSection,
    replaceText,
    summarizeSections,
)
from .database import closeClient, ensureIndexes, getDatabase
from .images import (
    ImageError,
    deleteImage,
    imageCacheSeconds,
    listImages,
    maxImageBytes,
    readImage,
    serializeImage,
    setImageAlt,
    storeImage,
    storedByteTotal,
)
from .schemas import (
    AdminCredentials,
    ApiKeyIssued,
    ApiKeyMetadata,
    ApiKeyRequest,
    ArticleCreate,
    ArticleOut,
    ArticleSummary,
    ArticleUpdate,
    BodyReplace,
    DraftBody,
    DraftCreate,
    DraftUpdate,
    ImageAltUpdate,
    ImageAsset,
    ImageAssetList,
    SectionInsert,
    SectionList,
    SectionUpdate,
    SubscriberAdminList,
    SubscriberCreate,
    SubscriberIssued,
    SubscriberOut,
    SubscriberUpdate,
)
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
from .seeding import applyPendingReseed, seedArticles, syncVersionedSeedArticles
from .sitemap import buildSitemap
from .subscribers import (
    issueOrRefreshSubscriber,
    listSubscribersForAdmin,
    requireSubscriber,
    serializeSubscriberOut,
    unsubscribeSubscriber,
    updateSubscriberName,
)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "untitled"


def serializeSeo(value: dict | None) -> dict:
    seo = value or {}
    return {
        "metaTitle": seo.get("metaTitle"),
        "metaDescription": seo.get("metaDescription"),
        "canonicalUrl": seo.get("canonicalUrl"),
        "keywords": list(seo.get("keywords", [])),
        "ogImageUrl": seo.get("ogImageUrl"),
        "noIndex": bool(seo.get("noIndex", False)),
    }


def serializeArticle(document: dict) -> dict:
    return {
        "id": str(document["_id"]),
        "title": document["title"],
        "slug": document["slug"],
        "summary": document.get("summary", ""),
        "bodyMarkdown": document.get("bodyMarkdown", ""),
        "publishedAt": document["publishedAt"],
        "status": document.get("status", "draft"),
        "aiAssisted": bool(document.get("aiAssisted", False)),
        "seo": serializeSeo(document.get("seo")),
        "heroImage": document.get("heroImage"),
        "sourceUrl": document.get("sourceUrl"),
        "createdAt": document["createdAt"],
        "updatedAt": document["updatedAt"],
    }


def apiBaseUrl(request: Request) -> str:
    """Where this API answers, so a stored image URL keeps working after a deploy."""
    configured = str(settings["publicApiUrl"])
    return configured or f"{str(request.base_url).rstrip('/')}/api"


def serializeSummary(document: dict) -> dict:
    article = serializeArticle(document)
    for field in ("bodyMarkdown", "sourceUrl", "createdAt", "seo", "heroImage"):
        article.pop(field, None)
    return article


@asynccontextmanager
async def lifespan(app: FastAPI):
    await applyPendingReseed(getDatabase())
    await applyPendingAuthMigration(getDatabase())
    await ensureIndexes()
    await seedArticles(getDatabase())
    await syncVersionedSeedArticles(getDatabase())
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


async def apiKeyOnly(request: Request, database: AsyncIOMotorDatabase = Depends(database)) -> dict:
    return await requireApiKeyRecord(database, request)


async def subscriberOnly(request: Request, database: AsyncIOMotorDatabase = Depends(database)) -> dict:
    return await requireSubscriber(database, request)


async def saveArticleUpdate(database: AsyncIOMotorDatabase, existing: dict, update: dict) -> dict:
    if "slug" in update:
        update["slug"] = slugify(update["slug"])
    update["updatedAt"] = datetime.now(UTC)
    try:
        await database.articles.update_one({"_id": existing["_id"]}, {"$set": update})
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail=f"the slug '{update.get('slug', '')}' is already taken") from error

    updatedSlug = update.get("slug", existing["slug"])
    if updatedSlug != existing["slug"]:
        await database.articleViews.update_many({"articleSlug": existing["slug"]}, {"$set": {"articleSlug": updatedSlug}})
    return serializeArticle(await database.articles.find_one({"slug": updatedSlug}))


async def loadArticleForApiKey(database: AsyncIOMotorDatabase, slug: str) -> dict:
    article = await database.articles.find_one({"slug": slug})
    if not article:
        raise HTTPException(status_code=404, detail="article not found")
    return article


async def loadEditableDraft(database: AsyncIOMotorDatabase, slug: str) -> dict:
    article = await loadArticleForApiKey(database, slug)
    if article.get("status", "draft") != "draft":
        raise HTTPException(
            status_code=409,
            detail="this article is published and is read-only for API keys; only the admin can change published work",
        )
    return article


def recordAiAssistance(update: dict) -> dict:
    """Every key-authenticated write marks the article, so the badge cannot be avoided."""
    return {**update, "aiAssisted": True}


async def saveBodyEdit(database: AsyncIOMotorDatabase, article: dict, edit) -> dict:
    try:
        bodyMarkdown = edit(article.get("bodyMarkdown", ""))
    except ContentEditError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return await saveArticleUpdate(database, article, recordAiAssistance({"bodyMarkdown": bodyMarkdown}))


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


@app.get("/api/images/{imageId}", response_class=Response)
async def getImage(imageId: str, database: AsyncIOMotorDatabase = Depends(database)) -> Response:
    """Serve a stored image. The id is a digest of the bytes, so this can never go stale."""
    record = await readImage(database, imageId)
    if not record:
        raise HTTPException(status_code=404, detail="image not found")
    return Response(
        content=bytes(record["data"]),
        media_type=record.get("contentType", "application/octet-stream"),
        headers={
            "Cache-Control": f"public, max-age={imageCacheSeconds}, immutable",
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.post("/api/admin/images", response_model=ImageAsset, dependencies=[Depends(adminOnly)])
async def uploadImage(request: Request, database: AsyncIOMotorDatabase = Depends(database)) -> dict:
    """Take raw image bytes from the editor and hand back the URL to write into Markdown.

    The body is the file itself rather than a multipart form: the editor already
    holds the bytes after a paste, and the declared content type is ignored in
    favour of what the bytes actually prove they are.
    """
    declaredLength = int(request.headers.get("content-length") or 0)
    if declaredLength > maxImageBytes:
        raise HTTPException(status_code=413, detail=f"images must be {maxImageBytes // (1024 * 1024)}MB or smaller")

    data = await request.body()
    try:
        stored = await storeImage(
            database,
            data,
            request.headers.get("x-image-filename", ""),
            request.headers.get("x-image-alt", ""),
            await authenticatedAdminEmail(database, request) or "",
        )
    except ImageError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return serializeImage(stored, apiBaseUrl(request))


@app.get("/api/admin/images", response_model=ImageAssetList, dependencies=[Depends(adminOnly)])
async def adminListImages(request: Request, database: AsyncIOMotorDatabase = Depends(database)) -> dict:
    images = await listImages(database)
    bytesUsed = await storedByteTotal(database)
    budget = int(settings["imageStorageMaxBytes"])
    return {
        "total": len(images),
        "bytesUsed": bytesUsed,
        "bytesAvailable": max(budget - bytesUsed, 0),
        "images": [serializeImage(image, apiBaseUrl(request)) for image in images],
    }


@app.patch("/api/admin/images/{imageId}", response_model=ImageAsset, dependencies=[Depends(adminOnly)])
async def adminUpdateImageAlt(
    imageId: str,
    payload: ImageAltUpdate,
    request: Request,
    database: AsyncIOMotorDatabase = Depends(database),
) -> dict:
    if not await readImage(database, imageId):
        raise HTTPException(status_code=404, detail="image not found")
    return serializeImage(await setImageAlt(database, imageId, payload.alt), apiBaseUrl(request))


@app.delete("/api/admin/images/{imageId}", dependencies=[Depends(adminOnly)])
async def adminDeleteImage(imageId: str, database: AsyncIOMotorDatabase = Depends(database)) -> dict[str, bool]:
    """Remove an image only once nothing points at it, so no article loses a picture."""
    if not await readImage(database, imageId):
        raise HTTPException(status_code=404, detail="image not found")
    referencing = await deleteImage(database, imageId)
    if referencing:
        raise HTTPException(
            status_code=409,
            detail=f"this image is still used by {', '.join(referencing)}; remove it there first",
        )
    return {"deleted": True}


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
    # heroImage is the one field where an explicit null means "remove the image".
    submitted = payload.model_dump(exclude_unset=True)
    update = {key: value for key, value in submitted.items() if value is not None or key == "heroImage"}
    return await saveArticleUpdate(database, existing, update)


@app.get("/api/admin/api-key", response_model=ApiKeyMetadata, dependencies=[Depends(adminOnly)])
async def adminGetApiKey(database: AsyncIOMotorDatabase = Depends(database)) -> dict:
    return serializeApiKey(await getApiKeyRecord(database))


@app.post("/api/admin/api-key", response_model=ApiKeyIssued)
async def adminCreateApiKey(
    payload: ApiKeyRequest,
    request: Request,
    database: AsyncIOMotorDatabase = Depends(database),
) -> dict:
    """Issue the single active key. Any previous key stops working immediately."""
    email = await requireAdmin(database, request)
    key, metadata = await issueApiKey(database, email, payload.label)
    return {**metadata, "key": key}


@app.delete("/api/admin/api-key", dependencies=[Depends(adminOnly)])
async def adminRevokeApiKey(database: AsyncIOMotorDatabase = Depends(database)) -> dict[str, bool]:
    return {"revoked": await revokeApiKey(database)}


@app.get("/api/content/whoami")
async def contentWhoami(record: dict = Depends(apiKeyOnly)) -> dict[str, object]:
    return {
        "authenticated": True,
        "scope": record.get("scope", "articles:draft"),
        "label": record.get("label", ""),
        "hint": record.get("hint", ""),
        "canPublish": False,
        "permissions": [
            "read published and draft articles",
            "create drafts",
            "edit draft title, slug, summary, body, sections, SEO fields and images",
        ],
        "restrictions": [
            "cannot publish or unpublish an article",
            "cannot modify an article whose status is published",
            "cannot delete articles",
            "cannot set aiAssisted; every edit made with this key marks the article as AI-assisted",
        ],
    }


@app.get("/api/content/articles", response_model=list[ArticleSummary])
async def contentListArticles(
    status: str | None = None,
    database: AsyncIOMotorDatabase = Depends(database),
    record: dict = Depends(apiKeyOnly),
) -> list[dict]:
    if status is not None and status not in {"draft", "published"}:
        raise HTTPException(status_code=422, detail="status filter must be 'draft' or 'published'")
    query = {"status": status} if status else {}
    cursor = database.articles.find(query).sort("publishedAt", -1)
    return [serializeSummary(article) async for article in cursor]


@app.get("/api/content/articles/{slug}", response_model=ArticleOut)
async def contentGetArticle(
    slug: str,
    database: AsyncIOMotorDatabase = Depends(database),
    record: dict = Depends(apiKeyOnly),
) -> dict:
    return serializeArticle(await loadArticleForApiKey(database, slug))


@app.post("/api/content/articles", response_model=ArticleOut, status_code=201)
async def contentCreateDraft(
    payload: DraftCreate,
    database: AsyncIOMotorDatabase = Depends(database),
    record: dict = Depends(apiKeyOnly),
) -> dict:
    now = datetime.now(UTC)
    document = payload.model_dump()
    document["slug"] = slugify(document.pop("slug", None) or document["title"])
    document["publishedAt"] = document.get("publishedAt") or now
    document["status"] = "draft"
    document["aiAssisted"] = True
    document["createdAt"] = now
    document["updatedAt"] = now
    try:
        result = await database.articles.insert_one(document)
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail=f"the slug '{document['slug']}' is already taken") from error
    return serializeArticle(await database.articles.find_one({"_id": result.inserted_id}))


@app.patch("/api/content/articles/{slug}", response_model=ArticleOut)
async def contentUpdateDraft(
    slug: str,
    payload: DraftUpdate,
    database: AsyncIOMotorDatabase = Depends(database),
    record: dict = Depends(apiKeyOnly),
) -> dict:
    article = await loadEditableDraft(database, slug)
    update = payload.model_dump(exclude_unset=True)
    clearHeroImage = update.pop("clearHeroImage", False)
    update = {key: value for key, value in update.items() if value is not None}
    if clearHeroImage:
        update["heroImage"] = None
    if not update:
        raise HTTPException(status_code=422, detail="provide at least one field to update")
    return await saveArticleUpdate(database, article, recordAiAssistance(update))


@app.put("/api/content/articles/{slug}/body", response_model=ArticleOut)
async def contentReplaceBody(
    slug: str,
    payload: DraftBody,
    database: AsyncIOMotorDatabase = Depends(database),
    record: dict = Depends(apiKeyOnly),
) -> dict:
    article = await loadEditableDraft(database, slug)
    return await saveBodyEdit(database, article, lambda _body: payload.bodyMarkdown)


@app.post("/api/content/articles/{slug}/body/replace", response_model=ArticleOut)
async def contentReplaceText(
    slug: str,
    payload: BodyReplace,
    database: AsyncIOMotorDatabase = Depends(database),
    record: dict = Depends(apiKeyOnly),
) -> dict:
    article = await loadEditableDraft(database, slug)
    return await saveBodyEdit(
        database,
        article,
        lambda body: replaceText(body, payload.find, payload.replace, payload.expectedCount),
    )


@app.get("/api/content/articles/{slug}/sections", response_model=SectionList)
async def contentListSections(
    slug: str,
    database: AsyncIOMotorDatabase = Depends(database),
    record: dict = Depends(apiKeyOnly),
) -> dict:
    article = await loadArticleForApiKey(database, slug)
    status = article.get("status", "draft")
    return {
        "slug": article["slug"],
        "status": status,
        "editable": status == "draft",
        "sections": summarizeSections(article.get("bodyMarkdown", "")),
    }


@app.put("/api/content/articles/{slug}/sections/{sectionId}", response_model=ArticleOut)
async def contentUpdateSection(
    slug: str,
    sectionId: str,
    payload: SectionUpdate,
    database: AsyncIOMotorDatabase = Depends(database),
    record: dict = Depends(apiKeyOnly),
) -> dict:
    article = await loadEditableDraft(database, slug)
    return await saveBodyEdit(
        database,
        article,
        lambda body: replaceSection(body, sectionId, payload.heading, payload.body),
    )


@app.post("/api/content/articles/{slug}/sections", response_model=ArticleOut)
async def contentInsertSection(
    slug: str,
    payload: SectionInsert,
    database: AsyncIOMotorDatabase = Depends(database),
    record: dict = Depends(apiKeyOnly),
) -> dict:
    article = await loadEditableDraft(database, slug)
    return await saveBodyEdit(
        database,
        article,
        lambda body: insertSection(body, payload.heading, payload.body, payload.level, payload.after, payload.before),
    )


@app.delete("/api/content/articles/{slug}/sections/{sectionId}", response_model=ArticleOut)
async def contentDeleteSection(
    slug: str,
    sectionId: str,
    database: AsyncIOMotorDatabase = Depends(database),
    record: dict = Depends(apiKeyOnly),
) -> dict:
    article = await loadEditableDraft(database, slug)
    return await saveBodyEdit(database, article, lambda body: deleteSection(body, sectionId))


@app.post("/api/subscribers", response_model=SubscriberIssued, status_code=201)
async def createSubscriber(
    payload: SubscriberCreate,
    request: Request,
    database: AsyncIOMotorDatabase = Depends(database),
) -> dict:
    return await issueOrRefreshSubscriber(database, request, payload.email, payload.name, payload.source)


@app.get("/api/subscribers/me", response_model=SubscriberOut)
async def getSubscriberMe(record: dict = Depends(subscriberOnly)) -> dict:
    return serializeSubscriberOut(record)


@app.patch("/api/subscribers/me", response_model=SubscriberOut)
async def updateSubscriberMe(
    payload: SubscriberUpdate,
    database: AsyncIOMotorDatabase = Depends(database),
    record: dict = Depends(subscriberOnly),
) -> dict:
    updated = await updateSubscriberName(database, record, payload.name)
    return serializeSubscriberOut(updated)


@app.delete("/api/subscribers/me")
async def deleteSubscriberMe(
    database: AsyncIOMotorDatabase = Depends(database),
    record: dict = Depends(subscriberOnly),
) -> dict[str, bool]:
    return await unsubscribeSubscriber(database, record)


@app.get("/api/admin/subscribers", response_model=SubscriberAdminList, dependencies=[Depends(adminOnly)])
async def adminListSubscribers(database: AsyncIOMotorDatabase = Depends(database)) -> dict:
    return await listSubscribersForAdmin(database)
