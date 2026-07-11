import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from .config import getSettings

adminEmail = "me@jackhales.com"
passwordAlgorithm = "scrypt"
passwordN = 2**14
passwordR = 8
passwordP = 1
passwordLength = 32
passwordSaltLength = 16
passwordMaxMemory = 64 * 1024 * 1024
sessionDays = 30


def getClientIp(request: Request) -> str:
    forwardedFor = request.headers.get("x-forwarded-for", "")
    if forwardedFor:
        return forwardedFor.split(",")[0].strip()
    realIp = request.headers.get("x-real-ip")
    if realIp:
        return realIp.strip()
    return request.client.host if request.client else ""


def normalizeEmail(email: str) -> str:
    return email.strip().lower()


def hashPassword(password: str) -> str:
    salt = secrets.token_bytes(passwordSaltLength)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=passwordN,
        r=passwordR,
        p=passwordP,
        maxmem=passwordMaxMemory,
        dklen=passwordLength,
    )
    return "$".join(
        (
            passwordAlgorithm,
            str(passwordN),
            str(passwordR),
            str(passwordP),
            salt.hex(),
            digest.hex(),
        )
    )


def verifyPassword(password: str, storedHash: str) -> bool:
    try:
        algorithm, nValue, rValue, pValue, saltHex, expectedHex = storedHash.split("$", 5)
        if algorithm != passwordAlgorithm:
            return False
        n, r, p = int(nValue), int(rValue), int(pValue)
        if (n, r, p) != (passwordN, passwordR, passwordP):
            return False
        salt = bytes.fromhex(saltHex)
        expected = bytes.fromhex(expectedHex)
        if len(salt) != passwordSaltLength or len(expected) != passwordLength:
            return False
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            maxmem=passwordMaxMemory,
            dklen=len(expected),
        )
        return hmac.compare_digest(digest, expected)
    except (TypeError, ValueError):
        return False


def tokenHash(token: str) -> str:
    settings = getSettings()
    secret = str(settings["sessionSecret"]).encode()
    return hmac.new(secret, token.encode(), hashlib.sha256).hexdigest()


def viewIpHash(ip: str) -> str:
    settings = getSettings()
    secret = str(settings["sessionSecret"]).encode()
    return hmac.new(secret, f"article-view:{ip}".encode(), hashlib.sha256).hexdigest()


async def createSession(database: AsyncIOMotorDatabase, email: str) -> str:
    token = secrets.token_urlsafe(48)
    now = datetime.now(UTC)
    await database.adminSessions.insert_one(
        {
            "tokenHash": tokenHash(token),
            "userEmail": normalizeEmail(email),
            "createdAt": now,
            "expiresAt": now + timedelta(days=sessionDays),
        }
    )
    return token


async def authenticatedAdminEmail(database: AsyncIOMotorDatabase, request: Request) -> str | None:
    token = request.cookies.get("adminSession")
    if not token:
        return None
    session = await database.adminSessions.find_one(
        {"tokenHash": tokenHash(token), "expiresAt": {"$gt": datetime.now(UTC)}}
    )
    if not session:
        return None
    email = normalizeEmail(str(session.get("userEmail", "")))
    if email != adminEmail:
        return None
    user = await database.adminUsers.find_one({"_id": email, "email": email, "role": "admin"})
    return email if user else None


async def requireAdmin(database: AsyncIOMotorDatabase, request: Request) -> str:
    email = await authenticatedAdminEmail(database, request)
    if email is None:
        raise HTTPException(status_code=401, detail="admin session required")
    return email
