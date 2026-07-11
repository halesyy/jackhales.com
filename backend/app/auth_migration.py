import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


authMigrationTokenPath = Path(__file__).resolve().parent.parent / "seed" / "auth-migration.once"


def loadAuthMigrationToken(path: Path = authMigrationTokenPath) -> str | None:
    if not path.exists():
        return None
    token = path.read_text().strip()
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", token):
        raise ValueError("Invalid auth migration token")
    return token


async def backupLegacyAuth(database: Any) -> dict[str, list[dict[str, Any]]]:
    backup: dict[str, list[dict[str, Any]]] = {}
    for collectionName in ("adminConfig", "adminSessions"):
        backup[collectionName] = [document async for document in database[collectionName].find({})]
    return backup


async def applyPendingAuthMigration(database: Any) -> dict[str, int] | None:
    token = loadAuthMigrationToken()
    if token is None:
        return None

    operationId = f"auth:{token}"
    completedRun = await database.maintenanceRuns.find_one({"_id": operationId, "status": "completed"})
    if completedRun:
        return completedRun.get("summary")

    existingBackup = await database.maintenanceBackups.find_one({"_id": operationId}, {"_id": 1})
    if existingBackup is None:
        await database.maintenanceBackups.insert_one(
            {
                "_id": operationId,
                "createdAt": datetime.now(UTC),
                "collections": await backupLegacyAuth(database),
            }
        )

    await database.maintenanceRuns.update_one(
        {"_id": operationId},
        {"$setOnInsert": {"startedAt": datetime.now(UTC)}, "$set": {"status": "running"}},
        upsert=True,
    )
    configResult = await database.adminConfig.delete_many({})
    sessionResult = await database.adminSessions.delete_many({})
    summary = {
        "legacyAdminConfigDeleted": configResult.deleted_count,
        "legacyAdminSessionsDeleted": sessionResult.deleted_count,
    }
    await database.maintenanceRuns.update_one(
        {"_id": operationId},
        {"$set": {"status": "completed", "completedAt": datetime.now(UTC), "summary": summary}},
    )
    return summary
