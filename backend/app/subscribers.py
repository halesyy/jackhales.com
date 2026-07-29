import hashlib
import hmac
import secrets
import time

from fastapi import HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from .config import getSettings
from .security import getClientIp

tokenPrefix = "jhs"
tokenEnvironment = "live"
tokenSecretBytes = 32
userAgentMaxLength = 300
rateLimitWindowSeconds = 3600
rateLimitMaxNewPerHour = 5


def buildSubscriberToken() -> str:
    return f"{tokenPrefix}_{tokenEnvironment}_{secrets.token_urlsafe(tokenSecretBytes)}"


def subscriberTokenHash(token: str) -> str:
    settings = getSettings()
    secret = str(settings["sessionSecret"]).encode()
    return hmac.new(secret, f"subscriber-token:{token}".encode(), hashlib.sha256).hexdigest()


def readSubscriberToken(request: Request) -> str | None:
    """Accept either a bearer token or the dedicated header, never a query string."""
    authorization = request.headers.get("authorization", "")
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() == "bearer" and credentials.strip():
        return credentials.strip()
    header = request.headers.get("x-subscriber-token", "")
    return header.strip() or None


def serializeSubscriberIssued(document: dict, token: str) -> dict:
    return {
        "email": document["email"],
        "name": document.get("name", ""),
        "status": document.get("status", "active"),
        "createdUnix": document["createdUnix"],
        "updatedUnix": document["updatedUnix"],
        "token": token,
    }


def serializeSubscriberOut(document: dict) -> dict:
    return {
        "email": document["email"],
        "name": document.get("name", ""),
        "status": document.get("status", "active"),
        "createdUnix": document["createdUnix"],
        "updatedUnix": document["updatedUnix"],
    }


def serializeSubscriberAdmin(document: dict) -> dict:
    return {
        "id": str(document["_id"]),
        "email": document["email"],
        "name": document.get("name", ""),
        "status": document.get("status", "active"),
        "clientIp": document.get("clientIp", ""),
        "source": document.get("source", ""),
        "createdUnix": document["createdUnix"],
        "updatedUnix": document["updatedUnix"],
    }


async def countRecentSubscriptionsFromIp(database: AsyncIOMotorDatabase, ip: str) -> int:
    return await database.subscribers.count_documents(
        {"clientIp": ip, "createdUnix": {"$gt": time.time() - rateLimitWindowSeconds}}
    )


async def issueOrRefreshSubscriber(database: AsyncIOMotorDatabase, request: Request, email: str, name: str, source: str) -> dict:
    """Create or refresh a subscriber and return the same response shape either way.

    Existence of an email on the list is private, so a repeat subscribe must be
    indistinguishable from a fresh one: same status code, same body shape, just a
    rotated token.
    """
    clientIp = getClientIp(request)
    userAgent = request.headers.get("user-agent", "")[:userAgentMaxLength]
    token = buildSubscriberToken()
    now = time.time()

    existing = await database.subscribers.find_one({"email": email})
    if existing is None:
        if await countRecentSubscriptionsFromIp(database, clientIp) >= rateLimitMaxNewPerHour:
            raise HTTPException(status_code=429, detail="too many subscriptions from this address recently; try again later")
        document = {
            "email": email,
            "name": name,
            "status": "active",
            "tokenHash": subscriberTokenHash(token),
            "clientIp": clientIp,
            "userAgent": userAgent,
            "source": source,
            "createdUnix": now,
            "updatedUnix": now,
            "unsubscribedUnix": None,
        }
        try:
            result = await database.subscribers.insert_one(document)
            created = await database.subscribers.find_one({"_id": result.inserted_id})
            return serializeSubscriberIssued(created, token)
        except DuplicateKeyError:
            existing = await database.subscribers.find_one({"email": email})

    update = {
        "status": "active",
        "tokenHash": subscriberTokenHash(token),
        "clientIp": clientIp,
        "userAgent": userAgent,
        "updatedUnix": now,
        "unsubscribedUnix": None,
    }
    if name:
        update["name"] = name
    await database.subscribers.update_one({"_id": existing["_id"]}, {"$set": update})
    refreshed = await database.subscribers.find_one({"_id": existing["_id"]})
    return serializeSubscriberIssued(refreshed, token)


async def authenticateSubscriber(database: AsyncIOMotorDatabase, request: Request) -> dict | None:
    token = readSubscriberToken(request)
    if not token:
        return None
    return await database.subscribers.find_one({"tokenHash": subscriberTokenHash(token)})


async def requireSubscriber(database: AsyncIOMotorDatabase, request: Request) -> dict:
    record = await authenticateSubscriber(database, request)
    if record is None:
        raise HTTPException(
            status_code=401,
            detail="a valid subscriber token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return record


async def updateSubscriberName(database: AsyncIOMotorDatabase, record: dict, name: str) -> dict:
    now = time.time()
    await database.subscribers.update_one({"_id": record["_id"]}, {"$set": {"name": name, "updatedUnix": now}})
    return await database.subscribers.find_one({"_id": record["_id"]})


async def unsubscribeSubscriber(database: AsyncIOMotorDatabase, record: dict) -> dict:
    if record.get("status") != "unsubscribed":
        now = time.time()
        await database.subscribers.update_one(
            {"_id": record["_id"]},
            {"$set": {"status": "unsubscribed", "unsubscribedUnix": now, "updatedUnix": now}},
        )
    return {"unsubscribed": True}


async def listSubscribersForAdmin(database: AsyncIOMotorDatabase) -> dict:
    cursor = database.subscribers.find({}).sort("createdUnix", -1)
    subscribers = [serializeSubscriberAdmin(document) async for document in cursor]
    active = sum(1 for subscriber in subscribers if subscriber["status"] == "active")
    return {"total": len(subscribers), "active": active, "subscribers": subscribers}
