import unittest
from unittest.mock import patch

from fastapi import HTTPException, Request
from pydantic import ValidationError

from fakedb import FakeDatabase

from app.main import (
    adminListSubscribers,
    createSubscriber,
    deleteSubscriberMe,
    getSubscriberMe,
    updateSubscriberMe,
)
from app.schemas import SubscriberCreate, SubscriberUpdate
from app.subscribers import authenticateSubscriber, requireSubscriber, subscriberTokenHash


def requestFromIp(ip: str = "127.0.0.1", headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    return Request({"type": "http", "headers": headers or [], "client": (ip, 1234)})


def requestWithToken(token: str | None = None, header: str = "authorization") -> Request:
    headers = []
    if token is not None:
        value = f"Bearer {token}" if header == "authorization" else token
        headers.append((header.encode(), value.encode()))
    return Request({"type": "http", "headers": headers, "client": ("127.0.0.1", 1234)})


class SubscribersTest(unittest.IsolatedAsyncioTestCase):
    async def testSubscribingStoresEmailNameIpAndCreatedUnixAndOnlyTheTokenHash(self) -> None:
        database = FakeDatabase()
        payload = SubscriberCreate(email=" Ada@Example.com ", name=" Ada ", source="/articles")

        result = await createSubscriber(payload, requestFromIp("203.0.113.5"), database)

        self.assertEqual(result["email"], "ada@example.com")
        self.assertEqual(result["name"], "Ada")
        self.assertEqual(result["status"], "active")
        self.assertIsInstance(result["createdUnix"], float)
        self.assertEqual(result["createdUnix"], result["updatedUnix"])
        self.assertTrue(result["token"].startswith("jhs_live_"))

        stored = await database.subscribers.find_one({"email": "ada@example.com"})
        self.assertEqual(stored["clientIp"], "203.0.113.5")
        self.assertEqual(stored["source"], "/articles")
        self.assertEqual(stored["tokenHash"], subscriberTokenHash(result["token"]))
        self.assertNotIn(result["token"], str(stored))

    async def testSubscribingAgainReturnsTheSameShapeAndRotatesTheToken(self) -> None:
        database = FakeDatabase()
        first = await createSubscriber(SubscriberCreate(email="repeat@example.com"), requestFromIp("203.0.113.5"), database)

        second = await createSubscriber(
            SubscriberCreate(email="Repeat@Example.com"), requestFromIp("203.0.113.6"), database
        )

        self.assertEqual(len(database.subscribers.documents), 1)
        self.assertEqual(set(first.keys()), set(second.keys()))
        self.assertEqual(second["createdUnix"], first["createdUnix"])
        self.assertNotEqual(second["token"], first["token"])

        self.assertIsNone(await authenticateSubscriber(database, requestWithToken(first["token"])))
        self.assertIsNotNone(await authenticateSubscriber(database, requestWithToken(second["token"])))

    async def testRepeatSubscribeKeepsExistingNameUnlessANewOneIsSupplied(self) -> None:
        database = FakeDatabase()
        await createSubscriber(SubscriberCreate(email="named@example.com", name="Original"), requestFromIp(), database)

        keptName = await createSubscriber(SubscriberCreate(email="named@example.com"), requestFromIp(), database)
        overwritten = await createSubscriber(
            SubscriberCreate(email="named@example.com", name="Replacement"), requestFromIp(), database
        )

        self.assertEqual(keptName["name"], "Original")
        self.assertEqual(overwritten["name"], "Replacement")

    async def testTheTokenUpdatesTheNameViaPatchAndBumpsUpdatedUnix(self) -> None:
        database = FakeDatabase()
        with patch("app.subscribers.time.time", return_value=1000.0):
            issued = await createSubscriber(SubscriberCreate(email="patch@example.com"), requestFromIp(), database)
        record = await requireSubscriber(database, requestWithToken(issued["token"]))
        self.assertEqual(record["updatedUnix"], 1000.0)

        with patch("app.subscribers.time.time", return_value=2000.0):
            updated = await updateSubscriberMe(SubscriberUpdate(name="New Name"), database, record)

        self.assertEqual(updated["name"], "New Name")
        self.assertEqual(updated["updatedUnix"], 2000.0)

    async def testGetMeNeverExposesClientIpOrToken(self) -> None:
        database = FakeDatabase()
        issued = await createSubscriber(SubscriberCreate(email="private@example.com"), requestFromIp("203.0.113.9"), database)
        record = await requireSubscriber(database, requestWithToken(issued["token"]))

        result = await getSubscriberMe(record)

        self.assertNotIn("clientIp", result)
        self.assertNotIn("token", result)
        self.assertNotIn("tokenHash", result)

    async def testUnknownMissingAndMalformedTokensAllRaiseAnIdentical401(self) -> None:
        database = FakeDatabase()
        await createSubscriber(SubscriberCreate(email="known@example.com"), requestFromIp(), database)

        requests = [
            requestWithToken(None),
            requestWithToken("jhs_live_not-a-real-token"),
            requestWithToken(""),
            requestWithToken("garbage", header="x-subscriber-token"),
        ]
        details = set()
        for request in requests:
            with self.assertRaises(HTTPException) as context:
                await requireSubscriber(database, request)
            self.assertEqual(context.exception.status_code, 401)
            details.add(context.exception.detail)
        self.assertEqual(len(details), 1)

    async def testUnsubscribeFlipsStatusIsIdempotentAndKeepsTheRecord(self) -> None:
        database = FakeDatabase()
        issued = await createSubscriber(SubscriberCreate(email="leaving@example.com"), requestFromIp(), database)
        record = await requireSubscriber(database, requestWithToken(issued["token"]))

        first = await deleteSubscriberMe(database, record)
        stored = await database.subscribers.find_one({"email": "leaving@example.com"})
        firstUnsubscribedUnix = stored["unsubscribedUnix"]

        # A fresh dependency lookup, as a second real request would perform.
        secondRecord = await requireSubscriber(database, requestWithToken(issued["token"]))
        second = await deleteSubscriberMe(database, secondRecord)
        stillStored = await database.subscribers.find_one({"email": "leaving@example.com"})

        self.assertEqual(first, {"unsubscribed": True})
        self.assertEqual(second, {"unsubscribed": True})
        self.assertEqual(stillStored["status"], "unsubscribed")
        self.assertEqual(stillStored["unsubscribedUnix"], firstUnsubscribedUnix)
        self.assertEqual(len(database.subscribers.documents), 1)

    async def testEmailValidationRejectsJunkWith422(self) -> None:
        for junkEmail in (
            "not-an-email",
            "user@@example.com",
            "user@example",
            "@example.com",
            "user@.com",
            "a" * 250 + "@example.com",
        ):
            with self.assertRaises(ValidationError):
                SubscriberCreate(email=junkEmail)

    async def testTheIpRateLimitTripsAfterFiveNewRecordsButNotForARefresh(self) -> None:
        database = FakeDatabase()
        ip = "203.0.113.50"
        first = None
        for index in range(5):
            issued = await createSubscriber(SubscriberCreate(email=f"person{index}@example.com"), requestFromIp(ip), database)
            if first is None:
                first = issued

        with self.assertRaises(HTTPException) as context:
            await createSubscriber(SubscriberCreate(email="onemore@example.com"), requestFromIp(ip), database)
        self.assertEqual(context.exception.status_code, 429)

        refreshed = await createSubscriber(SubscriberCreate(email="person0@example.com"), requestFromIp(ip), database)
        self.assertNotEqual(refreshed["token"], first["token"])
        self.assertEqual(len(database.subscribers.documents), 5)

    async def testAdminListingReturnsTheCountPlusEmailsAndNamesNewestFirst(self) -> None:
        database = FakeDatabase()
        await database.subscribers.insert_one(
            {
                "email": "first@example.com",
                "name": "First",
                "status": "active",
                "tokenHash": "hash-1",
                "clientIp": "203.0.113.1",
                "userAgent": "",
                "source": "",
                "createdUnix": 1000.0,
                "updatedUnix": 1000.0,
                "unsubscribedUnix": None,
            }
        )
        await database.subscribers.insert_one(
            {
                "email": "second@example.com",
                "name": "Second",
                "status": "unsubscribed",
                "tokenHash": "hash-2",
                "clientIp": "203.0.113.2",
                "userAgent": "",
                "source": "",
                "createdUnix": 2000.0,
                "updatedUnix": 2000.0,
                "unsubscribedUnix": 2500.0,
            }
        )

        listing = await adminListSubscribers(database)

        self.assertEqual(listing["total"], 2)
        self.assertEqual(listing["active"], 1)
        self.assertEqual([subscriber["email"] for subscriber in listing["subscribers"]], ["second@example.com", "first@example.com"])
        self.assertEqual(listing["subscribers"][0]["name"], "Second")
        self.assertEqual(listing["subscribers"][0]["clientIp"], "203.0.113.2")


if __name__ == "__main__":
    unittest.main()
