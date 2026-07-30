import os
from functools import lru_cache


def splitCsv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache(maxsize=1)
def getSettings() -> dict[str, object]:
    return {
        "mongodbUrl": os.environ.get("MONGODB_URL", "mongodb://localhost:27017"),
        "mongodbDatabase": os.environ.get("MONGODB_DATABASE", "jackhales"),
        "sessionSecret": os.environ.get("SESSION_SECRET", "local-dev-session-secret"),
        "publicSiteUrl": os.environ.get("PUBLIC_SITE_URL", "https://jackhales.com").rstrip("/"),
        # Empty means "use the origin the request arrived on", which keeps image URLs
        # minted on a local backend pointing at that local backend.
        "publicApiUrl": os.environ.get("PUBLIC_API_URL", "").rstrip("/"),
        "corsOrigins": splitCsv(os.environ.get("CORS_ORIGINS", "")),
        # Images share MongoDB's volume with every other collection, so the library
        # gets an explicit ceiling rather than being allowed to fill the disk.
        "imageStorageMaxBytes": int(os.environ.get("IMAGE_STORAGE_MAX_BYTES", 256 * 1024 * 1024)),
    }
