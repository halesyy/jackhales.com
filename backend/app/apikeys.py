import hashlib
import hmac
import secrets
from datetime import UTC, datetime

from fastapi import HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from .config import getSettings

# One document identifier means the collection can only ever hold one active key.
activeKeyId = "active"
keyPrefix = "jhk"
keyEnvironment = "live"
keySecretBytes = 32
keyTailLength = 6
keyScope = "articles:draft"
keyLabelMaxLength = 80


def buildApiKey() -> str:
    return f"{keyPrefix}_{keyEnvironment}_{secrets.token_urlsafe(keySecretBytes)}"


def apiKeyHash(key: str) -> str:
    settings = getSettings()
    secret = str(settings["sessionSecret"]).encode()
    return hmac.new(secret, f"api-key:{key}".encode(), hashlib.sha256).hexdigest()


def apiKeyTail(key: str) -> str:
    return key[-keyTailLength:]


def apiKeyHint(key: str) -> str:
    return f"{keyPrefix}_{keyEnvironment}_…{apiKeyTail(key)}"


def serializeApiKey(document: dict | None) -> dict:
    if not document:
        return {"configured": False, "scope": keyScope}
    return {
        "configured": True,
        "label": document.get("label", ""),
        "hint": document.get("hint", ""),
        "scope": document.get("scope", keyScope),
        "createdAt": document.get("createdAt"),
        "createdBy": document.get("createdBy", ""),
        "lastUsedAt": document.get("lastUsedAt"),
    }


def readRequestKey(request: Request) -> str | None:
    """Accept either a bearer token or the dedicated header, never a query string."""
    authorization = request.headers.get("authorization", "")
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() == "bearer" and credentials.strip():
        return credentials.strip()
    header = request.headers.get("x-api-key", "")
    return header.strip() or None


async def issueApiKey(database: AsyncIOMotorDatabase, createdBy: str, label: str = "") -> tuple[str, dict]:
    """Replace any existing key with a new one and return the plaintext exactly once."""
    key = buildApiKey()
    document = {
        "_id": activeKeyId,
        "keyHash": apiKeyHash(key),
        "hint": apiKeyHint(key),
        "label": label.strip()[:keyLabelMaxLength],
        "scope": keyScope,
        "createdAt": datetime.now(UTC),
        "createdBy": createdBy,
        "lastUsedAt": None,
    }
    await database.apiKeys.replace_one({"_id": activeKeyId}, document, upsert=True)
    return key, serializeApiKey(document)


async def revokeApiKey(database: AsyncIOMotorDatabase) -> bool:
    result = await database.apiKeys.delete_one({"_id": activeKeyId})
    return bool(getattr(result, "deleted_count", 0))


async def getApiKeyRecord(database: AsyncIOMotorDatabase) -> dict | None:
    return await database.apiKeys.find_one({"_id": activeKeyId})


async def authenticateApiKey(database: AsyncIOMotorDatabase, request: Request) -> dict | None:
    key = readRequestKey(request)
    if not key:
        return None
    record = await getApiKeyRecord(database)
    if not record:
        return None
    if not hmac.compare_digest(str(record.get("keyHash", "")), apiKeyHash(key)):
        return None
    await database.apiKeys.update_one({"_id": activeKeyId}, {"$set": {"lastUsedAt": datetime.now(UTC)}})
    return record


async def requireApiKey(database: AsyncIOMotorDatabase, request: Request) -> dict:
    record = await authenticateApiKey(database, request)
    if record is None:
        raise HTTPException(
            status_code=401,
            detail="a valid Jack Hales API key is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return record
