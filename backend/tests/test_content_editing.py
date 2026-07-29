import unittest

from app.content import (
    ContentEditError,
    deleteSection,
    insertSection,
    replaceSection,
    replaceText,
    splitSections,
    summarizeSections,
)

article = """Some opening words before any heading.

## Background

Background paragraph one.

Background paragraph two.

## Method

```python
## not a heading, it lives inside a fence
print("hello")
```

Method body.

### Method detail

Detail body.

## Background

A second section that repeats an earlier heading.
"""


class SectionSplitTest(unittest.TestCase):
    def testPreambleHeadingsAndNestingAreAddressable(self) -> None:
        sections = splitSections(article)

        self.assertEqual(
            [(section["id"], section["level"]) for section in sections],
            [
                ("preamble", 0),
                ("background", 2),
                ("method", 2),
                ("method-detail", 3),
                ("background-2", 2),
            ],
        )

    def testHeadingsInsideCodeFencesAreNotSections(self) -> None:
        method = next(section for section in splitSections(article) if section["id"] == "method")

        self.assertIn("## not a heading", method["body"])
        self.assertNotIn("not-a-heading", [section["id"] for section in splitSections(article)])

    def testSummaryReportsSizeWithoutTouchingTheBody(self) -> None:
        summary = summarizeSections(article)

        background = next(section for section in summary if section["id"] == "background")
        self.assertEqual(background["heading"], "Background")
        self.assertEqual(background["words"], len(background["body"].split()))

    def testAnArticleWithNoHeadingsIsOnePreamble(self) -> None:
        sections = splitSections("Just a paragraph.")

        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]["id"], "preamble")


class SectionEditTest(unittest.TestCase):
    def testReplacingOneSectionLeavesEveryOtherLineUntouched(self) -> None:
        updated = replaceSection(article, "method", body="Replaced method body.")

        self.assertIn("## Method\n\nReplaced method body.\n\n### Method detail", updated)
        self.assertIn("Background paragraph one.", updated)
        self.assertIn("Some opening words before any heading.", updated)
        self.assertIn("A second section that repeats an earlier heading.", updated)
        self.assertNotIn('print("hello")', updated)

    def testRepeatedHeadingsAreEditedIndependently(self) -> None:
        updated = replaceSection(article, "background-2", body="Only the second one changed.")

        self.assertIn("Background paragraph one.", updated)
        self.assertIn("Only the second one changed.", updated)
        self.assertNotIn("A second section that repeats an earlier heading.", updated)

    def testHeadingCanBeRenamedWithoutLosingTheBody(self) -> None:
        updated = replaceSection(article, "method", heading="Approach")

        self.assertIn("## Approach", updated)
        self.assertIn("Method body.", updated)
        self.assertNotIn("## Method\n", updated)

    def testPreambleIsEditableButHasNoHeading(self) -> None:
        updated = replaceSection(article, "preamble", body="New opening.")
        self.assertTrue(updated.startswith("New opening.\n\n## Background"))

        with self.assertRaises(ContentEditError):
            replaceSection(article, "preamble", heading="Intro")

    def testSectionsCanBeAddressedByIndex(self) -> None:
        updated = replaceSection(article, "1", body="Indexed edit.")

        self.assertIn("## Background\n\nIndexed edit.", updated)

    def testUnknownSectionNamesTheAvailableSections(self) -> None:
        with self.assertRaises(ContentEditError) as context:
            replaceSection(article, "conclusion", body="x")

        self.assertIn("unknown section 'conclusion'", str(context.exception))
        self.assertIn("method-detail", str(context.exception))

    def testInsertPlacesASectionAfterOrBeforeATarget(self) -> None:
        after = insertSection(article, "Results", "Results body.", 2, after="method-detail")
        before = insertSection(article, "Summary", "Summary body.", 2, before="background")

        self.assertIn("Detail body.\n\n## Results\n\nResults body.\n", after)
        self.assertIn("## Summary\n\nSummary body.\n\n## Background", before)

    def testInsertRequiresExactlyOneAnchor(self) -> None:
        with self.assertRaises(ContentEditError):
            insertSection(article, "Results", "body", 2)
        with self.assertRaises(ContentEditError):
            insertSection(article, "Results", "body", 2, after="method", before="background")

    def testDeleteRemovesOnlyTheTargetSection(self) -> None:
        updated = deleteSection(article, "method-detail")

        self.assertNotIn("Detail body.", updated)
        self.assertIn("Method body.", updated)
        self.assertIn("A second section that repeats an earlier heading.", updated)


class TextReplacementTest(unittest.TestCase):
    def testUniqueTextIsReplaced(self) -> None:
        updated = replaceText(article, "Method body.", "Rewritten body.")

        self.assertIn("Rewritten body.", updated)

    def testAmbiguousReplacementNeedsAnExplicitCount(self) -> None:
        with self.assertRaises(ContentEditError) as context:
            replaceText(article, "Background", "History")

        self.assertIn("expectedCount", str(context.exception))
        self.assertEqual(replaceText(article, "Background", "History", 4).count("History"), 4)

    def testWrongCountIsRefusedBeforeAnythingChanges(self) -> None:
        with self.assertRaises(ContentEditError) as context:
            replaceText(article, "Background", "History", 2)

        self.assertIn("found 4", str(context.exception))

    def testMissingTextIsRefused(self) -> None:
        with self.assertRaises(ContentEditError):
            replaceText(article, "text that is not present", "x")


if __name__ == "__main__":
    unittest.main()
