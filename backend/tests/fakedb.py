"""A small in-memory stand-in for the Motor collections used by the API."""

from copy import deepcopy
from typing import Any


class FakeResult:
    def __init__(self, inserted_id: Any = None, deleted_count: int = 0, modified_count: int = 0) -> None:
        self.inserted_id = inserted_id
        self.upserted_id = inserted_id
        self.deleted_count = deleted_count
        self.modified_count = modified_count


class FakeCursor:
    def __init__(self, documents: list[dict]) -> None:
        self.documents = documents

    def sort(self, field: str, direction: int = 1) -> "FakeCursor":
        self.documents.sort(key=lambda document: document.get(field), reverse=direction < 0)
        return self

    async def __aiter__(self):
        for document in self.documents:
            yield deepcopy(document)


class FakeCollection:
    def __init__(self) -> None:
        self.documents: list[dict] = []
        self.nextId = 1

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

    def select(self, query: dict) -> list[dict]:
        return [document for document in self.documents if self.matches(document, query)]

    @staticmethod
    def project(document: dict, projection: dict | None) -> dict:
        """Mongo's two projection modes: name the fields to keep, or the ones to drop."""
        if not projection:
            return deepcopy(document)
        if any(projection.values()):
            return {key: deepcopy(document[key]) for key, included in projection.items() if included and key in document}
        return {key: deepcopy(value) for key, value in document.items() if projection.get(key, 1)}

    def find(self, query: dict | None = None, projection: dict | None = None) -> FakeCursor:
        return FakeCursor([self.project(document, projection) for document in self.select(query or {})])

    async def find_one(self, query: dict, projection: dict | None = None) -> dict | None:
        for document in self.select(query):
            return self.project(document, projection)
        return None

    async def insert_one(self, document: dict) -> FakeResult:
        stored = deepcopy(document)
        if "_id" not in stored:
            stored["_id"] = f"id-{self.nextId}"
            self.nextId += 1
        self.documents.append(stored)
        return FakeResult(inserted_id=stored["_id"])

    async def insert_many(self, documents: list[dict]) -> FakeResult:
        for document in documents:
            await self.insert_one(document)
        return FakeResult()

    async def replace_one(self, query: dict, document: dict, upsert: bool = False) -> FakeResult:
        matched = self.select(query)
        if matched:
            self.documents = [item for item in self.documents if item not in matched]
        if matched or upsert:
            self.documents.append(deepcopy(document))
        return FakeResult(modified_count=len(matched))

    async def update_one(self, query: dict, update: dict, upsert: bool = False) -> FakeResult:
        for document in self.documents:
            if self.matches(document, query):
                document.update(deepcopy(update.get("$set", {})))
                return FakeResult(modified_count=1)
        if upsert:
            merged = {**query, **update.get("$setOnInsert", {}), **update.get("$set", {})}
            return await self.insert_one(merged)
        return FakeResult()

    async def update_many(self, query: dict, update: dict) -> FakeResult:
        modified = 0
        for document in self.documents:
            if self.matches(document, query):
                document.update(deepcopy(update.get("$set", {})))
                modified += 1
        return FakeResult(modified_count=modified)

    async def delete_one(self, query: dict) -> FakeResult:
        for index, document in enumerate(self.documents):
            if self.matches(document, query):
                self.documents.pop(index)
                return FakeResult(deleted_count=1)
        return FakeResult()

    async def delete_many(self, query: dict) -> FakeResult:
        remaining = [document for document in self.documents if not self.matches(document, query)]
        removed = len(self.documents) - len(remaining)
        self.documents = remaining
        return FakeResult(deleted_count=removed)

    async def count_documents(self, query: dict) -> int:
        return len(self.select(query))

    async def estimated_document_count(self) -> int:
        return len(self.documents)


class FakeDatabase:
    def __init__(self) -> None:
        self.collections: dict[str, FakeCollection] = {}

    def __getattr__(self, name: str) -> FakeCollection:
        if name.startswith("_"):
            raise AttributeError(name)
        return self.collections.setdefault(name, FakeCollection())

    def __getitem__(self, name: str) -> FakeCollection:
        return getattr(self, name)
