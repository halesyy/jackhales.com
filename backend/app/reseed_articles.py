import argparse
import asyncio
import json
from typing import Any

from bson import json_util

from .database import closeClient, ensureIndexes, getDatabase
from .seeding import reseedArticles


async def backupCollections(database: Any) -> dict[str, list[dict[str, Any]]]:
    backup: dict[str, list[dict[str, Any]]] = {}
    for collectionName in ("articles", "articleViews", "adminSessions"):
        collection = database[collectionName]
        backup[collectionName] = [document async for document in collection.find({})]
    return backup


async def run(command: str) -> None:
    database = getDatabase()
    try:
        if command == "backup":
            print(json_util.dumps(await backupCollections(database)))
            return

        summary = await reseedArticles(database)
        await ensureIndexes()
        print(json.dumps(summary, sort_keys=True))
    finally:
        await closeClient()


def main() -> None:
    parser = argparse.ArgumentParser(description="Back up or reseed the Jack Hales article collections.")
    parser.add_argument("command", choices=("backup", "apply"))
    arguments = parser.parse_args()
    asyncio.run(run(arguments.command))


if __name__ == "__main__":
    main()
