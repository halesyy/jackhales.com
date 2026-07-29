import unittest
from datetime import UTC, datetime

from fastapi import HTTPException, Request
from pydantic import ValidationError

from fakedb import FakeDatabase

from app.apikeys import issueApiKey, requireApiKey
from app.main import (
    contentCreateDraft,
    contentDeleteSection,
    contentGetArticle,
    contentInsertSection,
    contentListArticles,
    contentListSections,
    contentReplaceBody,
    contentReplaceText,
    contentUpdateDraft,
    contentUpdateSection,
    contentWhoami,
)
from app.schemas import (
    ArticleSeo,
    BodyReplace,
    DraftBody,
    DraftCreate,
    DraftUpdate,
    SectionInsert,
    SectionUpdate,
)
from app.security import adminEmail

draftBody = """Opening paragraph.

## Findings

Original findings.

## Next steps

Original next steps.
"""


async def seedDatabase() -> tuple[FakeDatabase, dict]:
    database = FakeDatabase()
    key, _ = await issueApiKey(database, adminEmail)
    now = datetime.now(UTC)
    await database.articles.insert_one(
        {
            "_id": "draft-1",
            "title": "Draft article",
            "slug": "draft-article",
            "summary": "A draft.",
            "bodyMarkdown": draftBody,
            "status": "draft",
            "publishedAt": now,
            "createdAt": now,
            "updatedAt": now,
        }
    )
    await database.articles.insert_one(
        {
            "_id": "published-1",
            "title": "Published article",
            "slug": "published-article",
            "summary": "Live.",
            "bodyMarkdown": "## Live\n\nDo not touch.\n",
            "status": "published",
            "publishedAt": now,
            "createdAt": now,
            "updatedAt": now,
        }
    )
    record = await requireApiKey(database, Request({"type": "http", "headers": [(b"x-api-key", key.encode())], "client": None}))
    return database, record


class ContentApiTest(unittest.IsolatedAsyncioTestCase):
    async def testWhoamiStatesThatTheKeyCannotPublish(self) -> None:
        _database, record = await seedDatabase()

        identity = await contentWhoami(record)

        self.assertFalse(identity["canPublish"])
        self.assertEqual(identity["scope"], "articles:draft")
        self.assertTrue(any("cannot publish" in restriction for restriction in identity["restrictions"]))

    async def testReadAccessCoversDraftsAndPublishedWork(self) -> None:
        database, record = await seedDatabase()

        everything = await contentListArticles(None, database, record)
        drafts = await contentListArticles("draft", database, record)
        published = await contentGetArticle("published-article", database, record)

        self.assertEqual(len(everything), 2)
        self.assertEqual([article["slug"] for article in drafts], ["draft-article"])
        self.assertEqual(published["status"], "published")

    async def testCreatedArticlesAreAlwaysDrafts(self) -> None:
        database, record = await seedDatabase()

        created = await contentCreateDraft(DraftCreate(title="A brand new piece"), database, record)

        self.assertEqual(created["status"], "draft")
        self.assertEqual(created["slug"], "a-brand-new-piece")

    async def testPayloadsCannotCarryPublicationState(self) -> None:
        for payload in (
            {"title": "Sneaky", "status": "published"},
            {"title": "Sneaky", "publish": True},
        ):
            with self.assertRaises(ValidationError) as context:
                DraftCreate.model_validate(payload)
            self.assertIn("only the admin can publish", str(context.exception))

        with self.assertRaises(ValidationError) as context:
            DraftUpdate.model_validate({"status": "published"})
        self.assertIn("only the admin can publish", str(context.exception))

    async def testUnknownFieldsAreRejectedRatherThanIgnored(self) -> None:
        with self.assertRaises(ValidationError):
            DraftUpdate.model_validate({"title": "Fine", "isPublished": True})

    async def testEveryWriteRouteRefusesAPublishedArticle(self) -> None:
        database, record = await seedDatabase()
        slug = "published-article"
        writes = [
            contentUpdateDraft(slug, DraftUpdate(title="Rewritten"), database, record),
            contentReplaceBody(slug, DraftBody(bodyMarkdown="Replaced"), database, record),
            contentReplaceText(slug, BodyReplace(find="Do not touch.", replace="Touched"), database, record),
            contentUpdateSection(slug, "live", SectionUpdate(body="Rewritten"), database, record),
            contentInsertSection(slug, SectionInsert(heading="Extra", after="live"), database, record),
            contentDeleteSection(slug, "live", database, record),
        ]

        for write in writes:
            with self.assertRaises(HTTPException) as context:
                await write
            self.assertEqual(context.exception.status_code, 409)
            self.assertIn("read-only for API keys", context.exception.detail)

        untouched = await database.articles.find_one({"slug": slug})
        self.assertEqual(untouched["bodyMarkdown"], "## Live\n\nDo not touch.\n")
        self.assertEqual(untouched["title"], "Published article")

    async def testDraftMetadataSeoAndImagesCanBeUpdated(self) -> None:
        database, record = await seedDatabase()

        updated = await contentUpdateDraft(
            "draft-article",
            DraftUpdate(
                title="A sharper title",
                summary="A sharper summary.",
                seo=ArticleSeo(
                    metaTitle="A sharper title | Jack Hales",
                    metaDescription="Meta description.",
                    keywords=["research", " writing "],
                    ogImageUrl="https://jackhales.com/og.png",
                ),
                heroImage={"url": "/images/hero.png", "alt": "Hero"},
            ),
            database,
            record,
        )

        self.assertEqual(updated["title"], "A sharper title")
        self.assertEqual(updated["seo"]["keywords"], ["research", "writing"])
        self.assertEqual(updated["seo"]["ogImageUrl"], "https://jackhales.com/og.png")
        self.assertEqual(updated["heroImage"]["url"], "/images/hero.png")
        self.assertEqual(updated["status"], "draft")

    async def testUnsafeImageUrlsAreRejected(self) -> None:
        with self.assertRaises(ValidationError):
            ArticleSeo(ogImageUrl="javascript:alert(1)")

    async def testSectionEditsOnlyChangeTheTargetSection(self) -> None:
        database, record = await seedDatabase()

        sections = await contentListSections("draft-article", database, record)
        updated = await contentUpdateSection(
            "draft-article",
            "findings",
            SectionUpdate(body="Rewritten findings."),
            database,
            record,
        )

        self.assertTrue(sections["editable"])
        self.assertEqual([section["id"] for section in sections["sections"]], ["preamble", "findings", "next-steps"])
        self.assertIn("Rewritten findings.", updated["bodyMarkdown"])
        self.assertIn("Opening paragraph.", updated["bodyMarkdown"])
        self.assertIn("Original next steps.", updated["bodyMarkdown"])
        self.assertNotIn("Original findings.", updated["bodyMarkdown"])

    async def testAnEmptyUpdateIsRefused(self) -> None:
        database, record = await seedDatabase()

        with self.assertRaises(HTTPException) as context:
            await contentUpdateDraft("draft-article", DraftUpdate(), database, record)

        self.assertEqual(context.exception.status_code, 422)

    async def testAFailedSectionEditLeavesTheArticleUnchanged(self) -> None:
        database, record = await seedDatabase()

        with self.assertRaises(HTTPException) as context:
            await contentUpdateSection("draft-article", "conclusion", SectionUpdate(body="x"), database, record)

        self.assertEqual(context.exception.status_code, 422)
        self.assertEqual((await database.articles.find_one({"slug": "draft-article"}))["bodyMarkdown"], draftBody)

    async def testMissingArticlesReturnNotFound(self) -> None:
        database, record = await seedDatabase()

        with self.assertRaises(HTTPException) as context:
            await contentGetArticle("nothing-here", database, record)

        self.assertEqual(context.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
