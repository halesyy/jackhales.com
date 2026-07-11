import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from app.auth_migration import applyPendingAuthMigration, loadAuthMigrationToken


class FakeDeleteResult:
    def __init__(self, deletedCount: int) -> None:
        self.deleted_count = deletedCount


class FakeCursor:
    def __init__(self, documents: list[dict]) -> None:
        self.documents = documents

    def __aiter__(self):
        self.index = 0
        return self

    async def __anext__(self) -> dict:
        if self.index >= len(self.documents):
            raise StopAsyncIteration
        document = self.documents[self.index]
        self.index += 1
        return deepcopy(document)


class FakeCollection:
    def __init__(self, documents: list[dict] | None = None) -> None:
        self.documents = deepcopy(documents or [])

    def find(self, query: dict) -> FakeCursor:
        return FakeCursor([document for document in self.documents if self.matches(document, query)])

    async def find_one(self, query: dict, projection: dict | None = None) -> dict | None:
        for document in self.documents:
            if self.matches(document, query):
                if projection:
                    return {key: document[key] for key, included in projection.items() if included and key in document}
                return deepcopy(document)
        return None

    async def insert_one(self, document: dict) -> None:
        self.documents.append(deepcopy(document))

    async def delete_many(self, query: dict) -> FakeDeleteResult:
        retained = [document for document in self.documents if not self.matches(document, query)]
        result = FakeDeleteResult(len(self.documents) - len(retained))
        self.documents = retained
        return result

    async def update_one(self, query: dict, update: dict, upsert: bool = False) -> None:
        document = next((item for item in self.documents if self.matches(item, query)), None)
        if document is None and upsert:
            document = deepcopy(query)
            self.documents.append(document)
            document.update(deepcopy(update.get("$setOnInsert", {})))
        if document is not None:
            document.update(deepcopy(update.get("$set", {})))

    @staticmethod
    def matches(document: dict, query: dict) -> bool:
        return all(document.get(key) == value for key, value in query.items())


class FakeDatabase:
    def __init__(self) -> None:
        self.collections = {
            "adminConfig": FakeCollection([{"key": "pin", "pinHash": "legacy-secret"}]),
            "adminSessions": FakeCollection([{"tokenHash": "legacy-session"}]),
            "adminUsers": FakeCollection(),
            "maintenanceBackups": FakeCollection(),
            "maintenanceRuns": FakeCollection(),
        }

    def __getitem__(self, name: str) -> FakeCollection:
        return self.collections[name]

    def __getattr__(self, name: str) -> FakeCollection:
        return self.collections[name]


class AuthMigrationTest(unittest.IsolatedAsyncioTestCase):
    def testMigrationTokenIsValidated(self) -> None:
        with TemporaryDirectory() as directory:
            tokenPath = Path(directory) / "auth-migration.once"
            tokenPath.write_text("20260711-email-password-v1\n")
            self.assertEqual(loadAuthMigrationToken(tokenPath), "20260711-email-password-v1")

            tokenPath.write_text("../../unsafe")
            with self.assertRaises(ValueError):
                loadAuthMigrationToken(tokenPath)

    async def testMigrationBacksUpAndClearsLegacyAuthOnce(self) -> None:
        database = FakeDatabase()

        summary = await applyPendingAuthMigration(database)

        self.assertEqual(summary, {"legacyAdminConfigDeleted": 1, "legacyAdminSessionsDeleted": 1})
        self.assertEqual(database.adminConfig.documents, [])
        self.assertEqual(database.adminSessions.documents, [])
        self.assertEqual(len(database.maintenanceBackups.documents), 1)
        backup = database.maintenanceBackups.documents[0]["collections"]
        self.assertEqual(backup["adminConfig"][0]["pinHash"], "legacy-secret")
        self.assertEqual(backup["adminSessions"][0]["tokenHash"], "legacy-session")

        secondSummary = await applyPendingAuthMigration(database)
        self.assertEqual(secondSummary, summary)
        self.assertEqual(len(database.maintenanceBackups.documents), 1)


if __name__ == "__main__":
    unittest.main()
