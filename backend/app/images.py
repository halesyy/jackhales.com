"""Article images: sniff the bytes, store them once, serve them forever.

Images are content addressed — the id is a digest of the bytes — so the same
picture pasted into two articles is stored once and every URL this module mints
is immutable and safe to cache for a year.
"""

import hashlib
import time

from motor.motor_asyncio import AsyncIOMotorDatabase

from .config import getSettings

imageIdLength = 32
maxImageBytes = 8 * 1024 * 1024
maxImageDimension = 10000
altMaxLength = 300
filenameMaxLength = 120
imageCacheSeconds = 60 * 60 * 24 * 365
imagePathPrefix = "/images"

# Every format here can be dimension-probed from its header, which is what lets a
# figure reserve its space before the bytes arrive. SVG is deliberately absent:
# it is a script-carrying document, not a picture, and the editor rasterises it.
imageContentTypes = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
}


class ImageError(ValueError):
    """Raised when bytes are not an image this site will store or serve."""


def imageId(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:imageIdLength]


def readBigEndian(data: bytes) -> int:
    return int.from_bytes(data, "big")


def readLittleEndian(data: bytes) -> int:
    return int.from_bytes(data, "little")


def probePng(data: bytes) -> tuple[int, int] | None:
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) < 24 or data[12:16] != b"IHDR":
        return None
    return readBigEndian(data[16:20]), readBigEndian(data[20:24])


def probeGif(data: bytes) -> tuple[int, int] | None:
    if not (data.startswith(b"GIF87a") or data.startswith(b"GIF89a")) or len(data) < 10:
        return None
    return readLittleEndian(data[6:8]), readLittleEndian(data[8:10])


def probeJpeg(data: bytes) -> tuple[int, int] | None:
    """Walk the marker segments to the frame header that carries the real size."""
    if not data.startswith(b"\xff\xd8\xff"):
        return None

    position = 2
    length = len(data)
    while position + 9 < length:
        if data[position] != 0xFF:
            position += 1
            continue
        marker = data[position + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            position += 2
            continue
        segmentLength = readBigEndian(data[position + 2 : position + 4])
        if segmentLength < 2:
            return None
        # SOF0-SOF15 carry the frame size; DHT, JPG, DAC and DNL share the range.
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            return readBigEndian(data[position + 7 : position + 9]), readBigEndian(data[position + 5 : position + 7])
        position += 2 + segmentLength
    return None


def probeWebp(data: bytes) -> tuple[int, int] | None:
    if not data.startswith(b"RIFF") or len(data) < 30 or data[8:12] != b"WEBP":
        return None

    chunk = data[12:16]
    payload = data[20:]
    if chunk == b"VP8X" and len(payload) >= 10:
        return readLittleEndian(payload[4:7]) + 1, readLittleEndian(payload[7:10]) + 1
    if chunk == b"VP8 " and len(payload) >= 10 and payload[3:6] == b"\x9d\x01\x2a":
        return readLittleEndian(payload[6:8]) & 0x3FFF, readLittleEndian(payload[8:10]) & 0x3FFF
    if chunk == b"VP8L" and len(payload) >= 5 and payload[0] == 0x2F:
        bits = readLittleEndian(payload[1:5])
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None


imageProbes = (
    ("png", probePng),
    ("jpeg", probeJpeg),
    ("gif", probeGif),
    ("webp", probeWebp),
)


def probeImage(data: bytes) -> dict:
    """Turn untrusted bytes into a typed description, or refuse them.

    The declared content type of the upload is never trusted — the format is the
    one the bytes themselves prove, which is also what gets served back.
    """
    if not data:
        raise ImageError("the upload was empty")
    if len(data) > maxImageBytes:
        raise ImageError(f"images must be {maxImageBytes // (1024 * 1024)}MB or smaller")

    for name, probe in imageProbes:
        size = probe(data)
        if size is None:
            continue
        width, height = size
        if width < 1 or height < 1:
            raise ImageError("the image reports no width or height")
        if width > maxImageDimension or height > maxImageDimension:
            raise ImageError(f"images must be {maxImageDimension}px or smaller on each side")
        return {"contentType": imageContentTypes[name], "width": width, "height": height, "byteSize": len(data)}

    raise ImageError("only PNG, JPEG, GIF and WebP images can be stored")


def cleanFilename(value: str) -> str:
    name = value.replace("\\", "/").rsplit("/", 1)[-1].strip()
    return name[:filenameMaxLength]


def cleanAlt(value: str) -> str:
    return " ".join(value.split())[:altMaxLength]


def imageUrl(identifier: str, width: int, height: int, apiBaseUrl: str) -> str:
    """The one place an image URL is built.

    The dimensions ride along as query parameters so the renderer can reserve the
    figure's space without a round trip; a URL stripped of them still resolves.
    """
    return f"{apiBaseUrl.rstrip('/')}{imagePathPrefix}/{identifier}?w={width}&h={height}"


def serializeImage(document: dict, apiBaseUrl: str) -> dict:
    width = int(document.get("width", 0))
    height = int(document.get("height", 0))
    return {
        "id": str(document["_id"]),
        "url": imageUrl(str(document["_id"]), width, height, apiBaseUrl),
        "contentType": document.get("contentType", "application/octet-stream"),
        "width": width,
        "height": height,
        "byteSize": int(document.get("byteSize", 0)),
        "alt": document.get("alt", ""),
        "filename": document.get("filename", ""),
        "createdUnix": document.get("createdUnix", 0.0),
        "updatedUnix": document.get("updatedUnix", 0.0),
    }


def imageProjection() -> dict:
    """Every field except the bytes — a listing must never carry the payloads."""
    return {"data": 0}


async def storedByteTotal(database: AsyncIOMotorDatabase) -> int:
    total = 0
    async for document in database.articleImages.find({}, {"byteSize": 1}):
        total += int(document.get("byteSize", 0))
    return total


async def storeImage(
    database: AsyncIOMotorDatabase,
    data: bytes,
    filename: str,
    alt: str,
    uploadedBy: str,
) -> dict:
    """Store the bytes under their own digest, or adopt the copy already there."""
    probe = probeImage(data)
    identifier = imageId(data)
    now = time.time()

    existing = await database.articleImages.find_one({"_id": identifier}, imageProjection())
    if existing is not None:
        # The same picture pasted twice is the same record; a better alt still wins.
        if alt and not existing.get("alt"):
            return await setImageAlt(database, identifier, alt)
        return existing

    budget = int(getSettings()["imageStorageMaxBytes"])
    if await storedByteTotal(database) + len(data) > budget:
        raise ImageError(
            f"the image library is full at {budget // (1024 * 1024)}MB; remove an unused image before adding another"
        )

    await database.articleImages.insert_one(
        {
            "_id": identifier,
            "data": data,
            "contentType": probe["contentType"],
            "width": probe["width"],
            "height": probe["height"],
            "byteSize": probe["byteSize"],
            "alt": cleanAlt(alt),
            "filename": cleanFilename(filename),
            "uploadedBy": uploadedBy,
            "createdUnix": now,
            "updatedUnix": now,
        }
    )
    return await database.articleImages.find_one({"_id": identifier}, imageProjection())


async def readImage(database: AsyncIOMotorDatabase, identifier: str) -> dict | None:
    return await database.articleImages.find_one({"_id": identifier})


async def listImages(database: AsyncIOMotorDatabase) -> list[dict]:
    cursor = database.articleImages.find({}, imageProjection()).sort("createdUnix", -1)
    return [document async for document in cursor]


async def setImageAlt(database: AsyncIOMotorDatabase, identifier: str, alt: str) -> dict | None:
    await database.articleImages.update_one(
        {"_id": identifier},
        {"$set": {"alt": cleanAlt(alt), "updatedUnix": time.time()}},
    )
    return await database.articleImages.find_one({"_id": identifier}, imageProjection())


async def findImageReferences(database: AsyncIOMotorDatabase, identifier: str) -> list[str]:
    """Which articles would lose a picture if this image went away.

    The id is the digest, so a plain substring search over the places a URL can
    live finds every reference regardless of the query string carried with it.
    """
    cursor = database.articles.find({}, {"title": 1, "slug": 1, "bodyMarkdown": 1, "heroImage": 1, "seo": 1})
    referencing: list[str] = []
    async for article in cursor:
        hero = (article.get("heroImage") or {}).get("url", "")
        social = (article.get("seo") or {}).get("ogImageUrl") or ""
        haystack = f"{article.get('bodyMarkdown', '')}\n{hero}\n{social}"
        if identifier in haystack:
            referencing.append(article.get("title") or article.get("slug", ""))
    return referencing


async def deleteImage(database: AsyncIOMotorDatabase, identifier: str) -> list[str]:
    """Delete an unused image. Returns the articles that blocked the deletion."""
    referencing = await findImageReferences(database, identifier)
    if referencing:
        return referencing
    await database.articleImages.delete_one({"_id": identifier})
    return []
