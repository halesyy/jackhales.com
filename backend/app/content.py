import re

headingPattern = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
fencePattern = re.compile(r"^\s*(```|~~~)")
preambleId = "preamble"
maxHeadingLevel = 6


class ContentEditError(ValueError):
    """Raised when an edit cannot be applied to the article body safely."""


def anchorSlug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "section"


def scanHeadings(markdown: str) -> list[tuple[int, int, str]]:
    """Find ATX headings by line, skipping anything inside a fenced code block."""
    headings: list[tuple[int, int, str]] = []
    openFence = ""
    for number, line in enumerate(markdown.split("\n")):
        if openFence:
            if line.strip().startswith(openFence):
                openFence = ""
            continue
        fence = fencePattern.match(line)
        if fence:
            openFence = fence.group(1)
            continue
        heading = headingPattern.match(line)
        if heading:
            headings.append((number, len(heading.group(1)), heading.group(2).strip()))
    return headings


def splitSections(markdown: str) -> list[dict]:
    """Describe the article as addressable sections without rewriting the body."""
    lines = markdown.split("\n")
    headings = scanHeadings(markdown)
    starts = [heading[0] for heading in headings]
    sections: list[dict] = []
    usedIds: dict[str, int] = {}

    firstHeadingLine = starts[0] if starts else len(lines)
    preamble = "\n".join(lines[:firstHeadingLine])
    if preamble.strip():
        sections.append(
            {
                "id": preambleId,
                "index": 0,
                "level": 0,
                "heading": "",
                "body": preamble.strip("\n"),
                "startLine": 0,
                "endLine": firstHeadingLine,
            }
        )

    for position, (lineNumber, level, heading) in enumerate(headings):
        endLine = starts[position + 1] if position + 1 < len(starts) else len(lines)
        sections.append(
            {
                "id": uniqueSectionId(anchorSlug(heading), usedIds),
                "index": len(sections),
                "level": level,
                "heading": heading,
                "body": "\n".join(lines[lineNumber + 1 : endLine]).strip("\n"),
                "startLine": lineNumber,
                "endLine": endLine,
            }
        )
    return sections


def uniqueSectionId(slug: str, usedIds: dict[str, int]) -> str:
    usedIds[slug] = usedIds.get(slug, 0) + 1
    count = usedIds[slug]
    return slug if count == 1 else f"{slug}-{count}"


def summarizeSections(markdown: str) -> list[dict]:
    return [
        {
            "id": section["id"],
            "index": section["index"],
            "level": section["level"],
            "heading": section["heading"],
            "body": section["body"],
            "characters": len(section["body"]),
            "words": len(section["body"].split()),
        }
        for section in splitSections(markdown)
    ]


def findSection(markdown: str, sectionId: str) -> dict:
    sections = splitSections(markdown)
    for section in sections:
        if section["id"] == sectionId:
            return section
    if sectionId.isdigit():
        index = int(sectionId)
        for section in sections:
            if section["index"] == index:
                return section
    known = ", ".join(section["id"] for section in sections) or "none"
    raise ContentEditError(f"unknown section '{sectionId}'; available sections: {known}")


def trailingBlankCount(block: list[str]) -> int:
    count = 0
    for line in reversed(block):
        if line.strip():
            break
        count += 1
    return count


def replaceSection(markdown: str, sectionId: str, heading: str | None = None, body: str | None = None) -> str:
    """Rewrite one section in place, leaving every other line of the article untouched."""
    if heading is None and body is None:
        raise ContentEditError("provide a heading, a body, or both")

    section = findSection(markdown, sectionId)
    if heading is not None and not section["level"]:
        raise ContentEditError("the preamble has no heading to rename")

    lines = markdown.split("\n")
    original = lines[section["startLine"] : section["endLine"]]
    nextBody = section["body"] if body is None else body

    replacement: list[str] = []
    if section["level"]:
        nextHeading = section["heading"] if heading is None else heading.strip()
        if not nextHeading:
            raise ContentEditError("a section heading cannot be empty")
        replacement.append(f"{'#' * section['level']} {nextHeading}")
        if nextBody.strip():
            replacement.append("")
            replacement.extend(nextBody.strip("\n").split("\n"))
    elif nextBody.strip():
        replacement.extend(nextBody.strip("\n").split("\n"))

    replacement.extend([""] * trailingBlankCount(original))
    return "\n".join(lines[: section["startLine"]] + replacement + lines[section["endLine"] :])


def insertSection(
    markdown: str,
    heading: str,
    body: str = "",
    level: int = 2,
    after: str | None = None,
    before: str | None = None,
) -> str:
    if not heading.strip():
        raise ContentEditError("a section heading cannot be empty")
    if not 1 <= level <= maxHeadingLevel:
        raise ContentEditError(f"heading level must be between 1 and {maxHeadingLevel}")
    if (after is None) == (before is None):
        raise ContentEditError("provide exactly one of after or before")

    lines = markdown.split("\n")
    if after is not None:
        anchor = findSection(markdown, after)
        position = anchor["endLine"]
    else:
        anchor = findSection(markdown, str(before))
        position = anchor["startLine"]

    block = [f"{'#' * level} {heading.strip()}"]
    if body.strip():
        block.append("")
        block.extend(body.strip("\n").split("\n"))
    block.append("")

    if position > 0 and lines[position - 1].strip():
        block.insert(0, "")
    return "\n".join(lines[:position] + block + lines[position:])


def deleteSection(markdown: str, sectionId: str) -> str:
    section = findSection(markdown, sectionId)
    lines = markdown.split("\n")
    return "\n".join(lines[: section["startLine"]] + lines[section["endLine"] :])


def replaceText(markdown: str, find: str, replacement: str, expectedCount: int | None = None) -> str:
    """Exact-match replacement with an occurrence guard so a stray match cannot rewrite the article."""
    if not find:
        raise ContentEditError("the text to find cannot be empty")

    occurrences = markdown.count(find)
    if occurrences == 0:
        raise ContentEditError("the text to find does not appear in this article")
    if expectedCount is not None and occurrences != expectedCount:
        raise ContentEditError(f"expected {expectedCount} occurrences but found {occurrences}")
    if expectedCount is None and occurrences > 1:
        raise ContentEditError(f"found {occurrences} occurrences; pass expectedCount to confirm a multi-match replacement")
    return markdown.replace(find, replacement)
