import unittest

from fastapi import HTTPException, Request

from fakedb import FakeDatabase

from app.apikeys import (
    activeKeyId,
    apiKeyHash,
    authenticateApiKey,
    buildApiKey,
    getApiKeyRecord,
    issueApiKey,
    readRequestKey,
    requireApiKey,
    revokeApiKey,
)
from app.security import adminEmail


def requestWithKey(key: str | None = None, header: str = "authorization") -> Request:
    headers = []
    if key is not None:
        value = f"Bearer {key}" if header == "authorization" else key
        headers.append((header.encode(), value.encode()))
    return Request({"type": "http", "headers": headers, "client": ("127.0.0.1", 1234)})


class ApiKeyTest(unittest.IsolatedAsyncioTestCase):
    async def testIssuedKeyIsStoredAsAHashWithADisplayHintOnly(self) -> None:
        database = FakeDatabase()

        key, metadata = await issueApiKey(database, adminEmail, "plumb adapter")

        self.assertTrue(key.startswith("jhk_live_"))
        record = await getApiKeyRecord(database)
        self.assertEqual(record["_id"], activeKeyId)
        self.assertEqual(record["keyHash"], apiKeyHash(key))
        self.assertNotIn(key, str(record))
        self.assertTrue(metadata["configured"])
        self.assertEqual(metadata["label"], "plumb adapter")
        self.assertEqual(metadata["createdBy"], adminEmail)
        self.assertEqual(metadata["hint"], f"jhk_live_…{key[-6:]}")
        self.assertNotIn("key", metadata)

    async def testOnlyOneKeyExistsAndANewKeySupersedesTheOldOne(self) -> None:
        database = FakeDatabase()
        first, _ = await issueApiKey(database, adminEmail)

        second, _ = await issueApiKey(database, adminEmail)

        self.assertNotEqual(first, second)
        self.assertEqual(len(database.apiKeys.documents), 1)
        self.assertIsNone(await authenticateApiKey(database, requestWithKey(first)))
        self.assertIsNotNone(await authenticateApiKey(database, requestWithKey(second)))

    async def testBothBearerAndApiKeyHeadersAuthenticate(self) -> None:
        database = FakeDatabase()
        key, _ = await issueApiKey(database, adminEmail)

        self.assertIsNotNone(await authenticateApiKey(database, requestWithKey(key)))
        self.assertIsNotNone(await authenticateApiKey(database, requestWithKey(key, header="x-api-key")))

    async def testUnknownMissingAndMalformedKeysAreRejected(self) -> None:
        database = FakeDatabase()
        await issueApiKey(database, adminEmail)

        for request in (requestWithKey(None), requestWithKey(buildApiKey()), requestWithKey("")):
            with self.assertRaises(HTTPException) as context:
                await requireApiKey(database, request)
            self.assertEqual(context.exception.status_code, 401)

    async def testRevokedKeyStopsWorking(self) -> None:
        database = FakeDatabase()
        key, _ = await issueApiKey(database, adminEmail)

        self.assertTrue(await revokeApiKey(database))

        self.assertIsNone(await authenticateApiKey(database, requestWithKey(key)))
        self.assertFalse(await revokeApiKey(database))

    async def testSuccessfulUseRecordsLastUsedAt(self) -> None:
        database = FakeDatabase()
        key, _ = await issueApiKey(database, adminEmail)
        self.assertIsNone((await getApiKeyRecord(database))["lastUsedAt"])

        await requireApiKey(database, requestWithKey(key))

        self.assertIsNotNone((await getApiKeyRecord(database))["lastUsedAt"])

    def testKeyIsNeverReadFromAQueryStringOrOtherScheme(self) -> None:
        basic = Request({"type": "http", "headers": [(b"authorization", b"Basic abc123")], "client": None})
        query = Request({"type": "http", "headers": [], "query_string": b"key=jhk_live_secret", "client": None})

        self.assertIsNone(readRequestKey(basic))
        self.assertIsNone(readRequestKey(query))


if __name__ == "__main__":
    unittest.main()
