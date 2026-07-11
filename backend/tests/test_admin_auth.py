import unittest
from copy import deepcopy
from http.cookies import SimpleCookie

from fastapi import HTTPException, Request, Response

from app.main import adminStatus, bootstrapAdmin, loginAdmin
from app.schemas import AdminCredentials
from app.security import adminEmail, requireAdmin


class FakeCollection:
    def __init__(self) -> None:
        self.documents: list[dict] = []

    async def count_documents(self, query: dict) -> int:
        return len([document for document in self.documents if self.matches(document, query)])

    async def insert_one(self, document: dict) -> None:
        self.documents.append(deepcopy(document))

    async def find_one(self, query: dict, projection: dict | None = None) -> dict | None:
        for document in self.documents:
            if self.matches(document, query):
                if projection:
                    return {key: document[key] for key, included in projection.items() if included and key in document}
                return deepcopy(document)
        return None

    async def delete_many(self, query: dict) -> None:
        self.documents = [document for document in self.documents if not self.matches(document, query)]

    @staticmethod
    def matches(document: dict, query: dict) -> bool:
        for key, expected in query.items():
            actual = document.get(key)
            if isinstance(expected, dict) and "$gt" in expected:
                if actual is None or actual <= expected["$gt"]:
                    return False
            elif actual != expected:
                return False
        return True


class FakeDatabase:
    def __init__(self) -> None:
        self.adminUsers = FakeCollection()
        self.adminSessions = FakeCollection()


def requestWithSession(token: str | None = None) -> Request:
    headers = [] if token is None else [(b"cookie", f"adminSession={token}".encode())]
    return Request({"type": "http", "headers": headers, "client": ("127.0.0.1", 1234)})


class AdminAuthTest(unittest.IsolatedAsyncioTestCase):
    async def testFirstStartCreatesOnlyFixedAdminAndAuthenticatedSession(self) -> None:
        database = FakeDatabase()
        response = Response()
        credentials = AdminCredentials(email=" ME@JackHales.com ", password="correct horse battery staple")

        result = await bootstrapAdmin(credentials, response, database)

        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(database.adminUsers.documents), 1)
        user = database.adminUsers.documents[0]
        self.assertEqual(user["_id"], adminEmail)
        self.assertEqual(user["role"], "admin")
        self.assertNotEqual(user["passwordHash"], credentials.password)

        setCookie = response.headers["set-cookie"]
        self.assertIn("HttpOnly", setCookie)
        self.assertIn("Secure", setCookie)
        cookie = SimpleCookie()
        cookie.load(setCookie)
        token = cookie["adminSession"].value
        request = requestWithSession(token)

        self.assertEqual(await requireAdmin(database, request), adminEmail)
        self.assertEqual(
            await adminStatus(request, database),
            {"configured": True, "authenticated": True, "email": adminEmail},
        )

    async def testBootstrapRejectsAnyOtherEmail(self) -> None:
        database = FakeDatabase()
        credentials = AdminCredentials(email="someone@example.com", password="correct horse battery staple")

        with self.assertRaises(HTTPException) as context:
            await bootstrapAdmin(credentials, Response(), database)

        self.assertEqual(context.exception.status_code, 403)
        self.assertEqual(database.adminUsers.documents, [])

    async def testLoginRejectsWrongPassword(self) -> None:
        database = FakeDatabase()
        await bootstrapAdmin(
            AdminCredentials(email=adminEmail, password="correct horse battery staple"),
            Response(),
            database,
        )

        with self.assertRaises(HTTPException) as context:
            await loginAdmin(
                AdminCredentials(email=adminEmail, password="a completely wrong password"),
                Response(),
                database,
            )

        self.assertEqual(context.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
