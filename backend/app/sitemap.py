from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from html import escape
from urllib.parse import quote

STATIC_PATHS = (
    "",
    "/articles",
    "/background-and-experience",
    "/software-engineers-guide-exploring-oman-top-travel-tips-itinerary",
)


def _lastModified(value: object) -> str | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).date().isoformat()
    return None


def _urlElement(location: str, lastModified: str | None = None) -> str:
    fields = [f"<loc>{escape(location)}</loc>"]
    if lastModified:
        fields.append(f"<lastmod>{lastModified}</lastmod>")
    return f"  <url>{''.join(fields)}</url>"


def buildSitemap(siteUrl: str, articles: Iterable[Mapping[str, object]]) -> str:
    baseUrl = siteUrl.rstrip("/")
    urls = [_urlElement(f"{baseUrl}{path}") for path in STATIC_PATHS]

    seenSlugs: set[str] = set()
    for article in articles:
        slug = str(article.get("slug", "")).strip()
        if not slug or slug in seenSlugs:
            continue
        seenSlugs.add(slug)
        articleUrl = f"{baseUrl}/article/{quote(slug, safe='-._~')}"
        urls.append(_urlElement(articleUrl, _lastModified(article.get("updatedAt"))))

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n"
        "</urlset>\n"
    )
