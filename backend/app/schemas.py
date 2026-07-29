from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

publicationFields = ("status", "publish", "published", "publishedState")
maxKeywords = 25


def validateAssetUrl(value: str | None) -> str | None:
    if value is None:
        return None
    url = value.strip()
    if not url:
        return None
    if not (url.startswith("https://") or url.startswith("http://") or url.startswith("/")):
        raise ValueError("url must start with https://, http:// or /")
    return url


def validateSlugValue(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized.replace("-", "").replace("_", "").isalnum():
        raise ValueError("slug may contain letters, numbers, dashes, and underscores only")
    return normalized


class AdminCredentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=1024)

    @field_validator("email")
    @classmethod
    def normalizeEmail(cls, value: str) -> str:
        return value.strip().lower()


class ArticleSeo(BaseModel):
    metaTitle: str | None = Field(default=None, max_length=180)
    metaDescription: str | None = Field(default=None, max_length=320)
    canonicalUrl: str | None = Field(default=None, max_length=500)
    keywords: list[str] = Field(default_factory=list, max_length=maxKeywords)
    ogImageUrl: str | None = Field(default=None, max_length=500)
    noIndex: bool = False

    @field_validator("canonicalUrl", "ogImageUrl")
    @classmethod
    def validateUrls(cls, value: str | None) -> str | None:
        return validateAssetUrl(value)

    @field_validator("keywords")
    @classmethod
    def normalizeKeywords(cls, value: list[str]) -> list[str]:
        return [keyword.strip() for keyword in value if keyword.strip()]


class ArticleImage(BaseModel):
    url: str = Field(max_length=500)
    alt: str = Field(default="", max_length=300)
    caption: str = Field(default="", max_length=300)

    @field_validator("url")
    @classmethod
    def validateUrl(cls, value: str) -> str:
        url = validateAssetUrl(value)
        if not url:
            raise ValueError("an image needs a url")
        return url


class ArticleBase(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    slug: str = Field(min_length=1, max_length=220)
    summary: str = Field(default="", max_length=500)
    bodyMarkdown: str = Field(default="")
    publishedAt: datetime
    status: str = Field(default="draft", pattern="^(draft|published)$")
    seo: ArticleSeo = Field(default_factory=ArticleSeo)
    heroImage: ArticleImage | None = None

    @field_validator("slug")
    @classmethod
    def validateSlug(cls, value: str) -> str:
        return validateSlugValue(value)


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    slug: str | None = Field(default=None, min_length=1, max_length=220)
    summary: str | None = Field(default=None, max_length=500)
    bodyMarkdown: str | None = None
    publishedAt: datetime | None = None
    status: str | None = Field(default=None, pattern="^(draft|published)$")
    seo: ArticleSeo | None = None
    heroImage: ArticleImage | None = None

    @field_validator("slug")
    @classmethod
    def validateSlug(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validateSlugValue(value)


class ArticleOut(ArticleBase):
    id: str
    sourceUrl: str | None = None
    createdAt: datetime
    updatedAt: datetime


class ArticleSummary(BaseModel):
    id: str
    title: str
    slug: str
    summary: str
    publishedAt: datetime
    status: str
    updatedAt: datetime


class ApiKeyRequest(BaseModel):
    label: str = Field(default="", max_length=80)


class ApiKeyMetadata(BaseModel):
    configured: bool
    scope: str
    label: str = ""
    hint: str = ""
    createdAt: datetime | None = None
    createdBy: str = ""
    lastUsedAt: datetime | None = None


class ApiKeyIssued(ApiKeyMetadata):
    key: str


class DraftPayload(BaseModel):
    """Shared guardrail: an API key may never express publication state."""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def rejectPublicationFields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for field in publicationFields:
                if field in data:
                    raise ValueError(f"'{field}' cannot be set with an API key; only the admin can publish an article")
        return data


class DraftCreate(DraftPayload):
    title: str = Field(min_length=1, max_length=180)
    slug: str | None = Field(default=None, min_length=1, max_length=220)
    summary: str = Field(default="", max_length=500)
    bodyMarkdown: str = Field(default="")
    publishedAt: datetime | None = None
    seo: ArticleSeo = Field(default_factory=ArticleSeo)
    heroImage: ArticleImage | None = None

    @field_validator("slug")
    @classmethod
    def validateSlug(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validateSlugValue(value)


class DraftUpdate(DraftPayload):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    slug: str | None = Field(default=None, min_length=1, max_length=220)
    summary: str | None = Field(default=None, max_length=500)
    bodyMarkdown: str | None = None
    publishedAt: datetime | None = None
    seo: ArticleSeo | None = None
    heroImage: ArticleImage | None = None
    clearHeroImage: bool = False

    @field_validator("slug")
    @classmethod
    def validateSlug(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validateSlugValue(value)


class DraftBody(DraftPayload):
    bodyMarkdown: str


class SectionUpdate(DraftPayload):
    heading: str | None = Field(default=None, max_length=180)
    body: str | None = None


class SectionInsert(DraftPayload):
    heading: str = Field(min_length=1, max_length=180)
    body: str = ""
    level: int = Field(default=2, ge=1, le=6)
    after: str | None = None
    before: str | None = None


class BodyReplace(DraftPayload):
    find: str = Field(min_length=1)
    replace: str = ""
    expectedCount: int | None = Field(default=None, ge=1)


class SectionOut(BaseModel):
    id: str
    index: int
    level: int
    heading: str
    body: str
    characters: int
    words: int


class SectionList(BaseModel):
    slug: str
    status: str
    editable: bool
    sections: list[SectionOut]
