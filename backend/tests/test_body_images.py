import unittest
from datetime import UTC, datetime

from fastapi import HTTPException
from pydantic import ValidationError

from fakedb import FakeDatabase

from app.content import (
    ContentEditError,
    buildImageMarkdown,
    insertImage,
    moveImage,
    removeImage,
    summarizeBodyImages,
    updateImage,
)
from app.main import (
    contentInsertBodyImage,
    contentListBodyImages,
    contentRemoveBodyImage,
    contentUpdateBodyImage,
)
from app.schemas import BodyImageInsert, BodyImageUpdate

apiKeyRecord = {"label": "plumb adapter", "hint": "jhk_live_…abcd", "scope": "articles:draft"}

article = """Opening paragraph.

## Background

Some background prose.

![A wiring diagram](https://api.jackhales.com/api/images/aaa111?w=800&h=600 "How it wires up")

More background.

## Results

Results prose with an inline ![tiny badge](/badge.png) in the sentence.

```
![not a real image](/fenced.png)
```
"""


class BodyImageScanTest(unittest.TestCase):
    def testEveryImageIsFoundWithItsSectionAndShape(self) -> None:
        images = summarizeBodyImages(article)

        self.assertEqual([image["id"] for image in images], ["aaa111", "badge"])
        self.assertEqual(images[0]["sectionId"], "background")
        self.assertEqual(images[0]["alt"], "A wiring diagram")
        self.assertEqual(images[0]["caption"], "How it wires up")
        self.assertTrue(images[0]["standalone"])
        self.assertEqual(images[1]["sectionId"], "results")
        self.assertFalse(images[1]["standalone"])

    def testAnImageInAFencedCodeBlockIsNotAnImage(self) -> None:
        self.assertNotIn("fenced", [image["id"] for image in summarizeBodyImages(article)])

    def testAnUploadedImageIsIdentifiedByItsContentDigest(self) -> None:
        self.assertEqual(summarizeBodyImages(article)[0]["id"], "aaa111")

    def testRepeatedUrlsGetDistinctIds(self) -> None:
        body = "![one](/same.png)\n\n![two](/same.png)\n"
        self.assertEqual([image["id"] for image in summarizeBodyImages(body)], ["same", "same-2"])

    def testTheBlockWriterEscapesBracketsAndAddsTheCaptionAsATitle(self) -> None:
        self.assertEqual(
            buildImageMarkdown("/a.png", "Alt with [brackets]", "A caption"),
            '![Alt with \\[brackets\\]](/a.png "A caption")',
        )


class BodyImagePlacementTest(unittest.TestCase):
    def testAnImageLandsUnderTheHeadingWhenPlacedAtTheStartOfASection(self) -> None:
        updated = insertImage(article, "/new.png", "A new chart", section="results", position="start")
        lines = updated.split("\n")
        heading = lines.index("## Results")

        self.assertEqual(lines[heading + 2], "![A new chart](/new.png)")

    def testAnImageLandsAfterTheProseWhenPlacedAtTheEndOfASection(self) -> None:
        updated = insertImage(article, "/new.png", "A new chart", section="background", position="end")
        lines = updated.split("\n")

        self.assertLess(lines.index("More background."), lines.index("![A new chart](/new.png)"))
        self.assertLess(lines.index("![A new chart](/new.png)"), lines.index("## Results"))

    def testAnImageAlwaysSitsOnItsOwnLineWithBlankLinesAroundIt(self) -> None:
        updated = insertImage(article, "/new.png", "Chart", section="background", position="end")
        lines = updated.split("\n")
        at = lines.index("![Chart](/new.png)")

        self.assertEqual(lines[at - 1], "")
        self.assertEqual(lines[at + 1], "")

    def testACaptionBecomesTheMarkdownTitle(self) -> None:
        updated = insertImage(article, "/new.png", "Chart", caption="Figure 1", section="results", position="end")
        self.assertIn('![Chart](/new.png "Figure 1")', updated)

    def testAnImageWithNoSectionGoesToTheTopOrBottomOfTheBody(self) -> None:
        top = insertImage(article, "/new.png", "Chart", position="start")
        bottom = insertImage(article, "/new.png", "Chart", position="end")

        self.assertTrue(top.startswith("![Chart](/new.png)"))
        self.assertTrue(bottom.rstrip().endswith("![Chart](/new.png)"))

    def testAnImageNeedsAUrlAndAKnownPosition(self) -> None:
        with self.assertRaises(ContentEditError):
            insertImage(article, "   ", "Chart")
        with self.assertRaises(ContentEditError):
            insertImage(article, "/new.png", "Chart", position="middle")

    def testInsertingIntoAnUnknownSectionNamesTheSectionsThatExist(self) -> None:
        with self.assertRaises(ContentEditError) as caught:
            insertImage(article, "/new.png", "Chart", section="nowhere")

        self.assertIn("background", str(caught.exception))


class BodyImageMoveTest(unittest.TestCase):
    def testMovingAnImageTakesItOutOfOneSectionAndPutsItInAnother(self) -> None:
        updated = moveImage(article, "aaa111", "results", "start")
        images = summarizeBodyImages(updated)

        self.assertEqual(images[0]["sectionId"], "results")
        self.assertEqual(updated.count("aaa111"), 1)

    def testMovingPreservesAltAndCaption(self) -> None:
        updated = moveImage(article, "aaa111", "results", "end")
        moved = next(image for image in summarizeBodyImages(updated) if image["id"] == "aaa111")

        self.assertEqual(moved["alt"], "A wiring diagram")
        self.assertEqual(moved["caption"], "How it wires up")
        self.assertEqual(moved["sectionId"], "results")

    def testMovingDoesNotLeaveADoubleBlankLineBehind(self) -> None:
        updated = moveImage(article, "aaa111", "results", "end")
        self.assertNotIn("\n\n\n", updated)

    def testEveryOtherLineSurvivesAMove(self) -> None:
        updated = moveImage(article, "aaa111", "results", "end")
        for line in ("Opening paragraph.", "## Background", "Some background prose.", "More background.", "## Results"):
            self.assertIn(line, updated)

    def testAnImageInsideAParagraphCannotBeMoved(self) -> None:
        with self.assertRaises(ContentEditError) as caught:
            moveImage(article, "badge", "background", "end")

        self.assertIn("inside a paragraph", str(caught.exception))

    def testAnImageCanBeAddressedByIndexAsWellAsId(self) -> None:
        self.assertEqual(summarizeBodyImages(moveImage(article, "0", "results", "end"))[0]["sectionId"], "results")

    def testAnUnknownImageNamesTheOnesThatExist(self) -> None:
        with self.assertRaises(ContentEditError) as caught:
            moveImage(article, "nope", "results", "end")

        self.assertIn("aaa111", str(caught.exception))


class BodyImageEditTest(unittest.TestCase):
    def testAltTextCanBeCorrectedInPlace(self) -> None:
        updated = updateImage(article, "aaa111", alt="A clearer description")
        image = summarizeBodyImages(updated)[0]

        self.assertEqual(image["alt"], "A clearer description")
        self.assertEqual(image["caption"], "How it wires up")
        self.assertEqual(image["sectionId"], "background")

    def testACaptionCanBeAddedAndCleared(self) -> None:
        self.assertIn('"Figure 2"', updateImage(article, "aaa111", caption="Figure 2"))
        self.assertNotIn('"How it wires up"', updateImage(article, "aaa111", caption=""))

    def testTheUrlCanBeSwappedWithoutTouchingAnythingElse(self) -> None:
        updated = updateImage(article, "aaa111", url="/replacement.png")
        image = summarizeBodyImages(updated)[0]

        self.assertEqual(image["url"], "/replacement.png")
        self.assertEqual(image["alt"], "A wiring diagram")

    def testAnInlineImageIsEditedWithoutDisturbingItsSentence(self) -> None:
        updated = updateImage(article, "badge", alt="A small badge")

        self.assertIn("Results prose with an inline ![A small badge](/badge.png) in the sentence.", updated)

    def testAnEmptyEditIsRefused(self) -> None:
        with self.assertRaises(ContentEditError):
            updateImage(article, "aaa111")


class BodyImageRemovalTest(unittest.TestCase):
    def testRemovingAStandaloneImageLeavesTheProseSpacedAsItWas(self) -> None:
        updated = removeImage(article, "aaa111")

        self.assertNotIn("aaa111", updated)
        self.assertNotIn("\n\n\n", updated)
        self.assertIn("Some background prose.", updated)
        self.assertIn("More background.", updated)

    def testRemovingAnInlineImageKeepsTheSentence(self) -> None:
        updated = removeImage(article, "badge")

        self.assertNotIn("/badge.png", updated)
        self.assertIn("Results prose with an inline", updated)


class BodyImageEndpointTest(unittest.IsolatedAsyncioTestCase):
    """The image routes inherit the same guardrails every other body edit has."""

    async def seedArticle(self, status: str = "draft") -> FakeDatabase:
        database = FakeDatabase()
        now = datetime(2026, 7, 30, tzinfo=UTC)
        await database.articles.insert_one(
            {
                "title": "A draft",
                "slug": "a-draft",
                "status": status,
                "bodyMarkdown": article,
                "aiAssisted": False,
                "publishedAt": now,
                "createdAt": now,
                "updatedAt": now,
            }
        )
        return database

    async def testListingReportsWhereEachImageSits(self) -> None:
        database = await self.seedArticle()

        listing = await contentListBodyImages("a-draft", database, apiKeyRecord)

        self.assertTrue(listing["editable"])
        self.assertEqual([image["id"] for image in listing["images"]], ["aaa111", "badge"])

    async def testInsertingMarksTheArticleAiAssisted(self) -> None:
        database = await self.seedArticle()

        updated = await contentInsertBodyImage(
            "a-draft",
            BodyImageInsert(url="/new.png", alt="A chart", section="results", position="start"),
            database,
            apiKeyRecord,
        )

        self.assertTrue(updated["aiAssisted"])
        self.assertIn("![A chart](/new.png)", updated["bodyMarkdown"])

    async def testMovingAndEditingInOneRequestKeepsBothChanges(self) -> None:
        database = await self.seedArticle()

        updated = await contentUpdateBodyImage(
            "a-draft",
            "aaa111",
            BodyImageUpdate(alt="Rewritten alt", section="results", position="end"),
            database,
            apiKeyRecord,
        )

        moved = next(image for image in summarizeBodyImages(updated["bodyMarkdown"]) if image["id"] == "aaa111")
        self.assertEqual(moved["alt"], "Rewritten alt")
        self.assertEqual(moved["sectionId"], "results")

    async def testAnEmptyUpdateIsRefused(self) -> None:
        database = await self.seedArticle()

        with self.assertRaises(HTTPException) as caught:
            await contentUpdateBodyImage("a-draft", "aaa111", BodyImageUpdate(), database, apiKeyRecord)

        self.assertEqual(caught.exception.status_code, 422)

    async def testRemovingTakesItOutOfTheBodyOnly(self) -> None:
        database = await self.seedArticle()

        updated = await contentRemoveBodyImage("a-draft", "aaa111", database, apiKeyRecord)

        self.assertNotIn("aaa111", updated["bodyMarkdown"])

    async def testEveryImageRouteRefusesAPublishedArticle(self) -> None:
        database = await self.seedArticle(status="published")
        calls = [
            contentInsertBodyImage("a-draft", BodyImageInsert(url="/new.png"), database, apiKeyRecord),
            contentUpdateBodyImage("a-draft", "aaa111", BodyImageUpdate(alt="x"), database, apiKeyRecord),
            contentRemoveBodyImage("a-draft", "aaa111", database, apiKeyRecord),
        ]
        for call in calls:
            with self.subTest(call=call.__qualname__ if hasattr(call, "__qualname__") else "call"):
                with self.assertRaises(HTTPException) as caught:
                    await call
                self.assertEqual(caught.exception.status_code, 409)

    async def testAnUnknownImageIsAnActionable422(self) -> None:
        database = await self.seedArticle()

        with self.assertRaises(HTTPException) as caught:
            await contentRemoveBodyImage("a-draft", "nope", database, apiKeyRecord)

        self.assertEqual(caught.exception.status_code, 422)
        self.assertIn("aaa111", caught.exception.detail)

    async def testAPublicationFieldCannotRideAlongWithAnImageEdit(self) -> None:
        with self.assertRaises(ValidationError):
            BodyImageInsert(url="/new.png", status="published")


if __name__ == "__main__":
    unittest.main()
