from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

publicationFields = ("status", "publish", "published", "publishedState")
# The API sets this itself on every key-authenticated write, so a key may not
# declare it — an agent must not be able to hide or claim its own involvement.
automaticFields = ("aiAssisted",)
maxKeywords = 25
imageAltMaxLength = 300
subscriberEmailMaxLength = 254
subscriberNameMaxLength = 120
subscriberSourceMaxLength = 200


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


def validateSubscriberEmail(value: str) -> str:
    email = value.strip().lower()
    if not email or len(email) > subscriberEmailMaxLength or email.count("@") != 1:
        raise ValueError("enter a valid email address")
    localPart, domain = email.split("@")
    if not localPart or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise ValueError("enter a valid email address")
    return email


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
    aiAssisted: bool = False
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
    aiAssisted: bool | None = None
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
    aiAssisted: bool = False
    updatedAt: datetime


class ImageAsset(BaseModel):
    """A stored image. `url` is content addressed, so it never changes meaning."""

    id: str
    url: str
    contentType: str
    width: int
    height: int
    byteSize: int
    alt: str = ""
    filename: str = ""
    createdUnix: float
    updatedUnix: float


class ImageAssetList(BaseModel):
    total: int
    bytesUsed: int
    bytesAvailable: int
    images: list[ImageAsset]


class ImageAltUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alt: str = Field(default="", max_length=imageAltMaxLength)


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
            for field in automaticFields:
                if field in data:
                    raise ValueError(f"'{field}' is recorded automatically on every API-key edit and cannot be set by hand")
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


class BodyImageInsert(DraftPayload):
    url: str = Field(min_length=1, max_length=500)
    alt: str = Field(default="", max_length=imageAltMaxLength)
    caption: str = Field(default="", max_length=300)
    section: str | None = None
    position: str = Field(default="end", pattern="^(start|end)$")

    @field_validator("url")
    @classmethod
    def validateUrl(cls, value: str) -> str:
        url = validateAssetUrl(value)
        if not url:
            raise ValueError("an image needs a url")
        return url


class BodyImageUpdate(DraftPayload):
    """Alt, caption and url edit in place; section and position move the image."""

    alt: str | None = Field(default=None, max_length=imageAltMaxLength)
    caption: str | None = Field(default=None, max_length=300)
    url: str | None = Field(default=None, max_length=500)
    section: str | None = None
    position: str | None = Field(default=None, pattern="^(start|end)$")

    @field_validator("url")
    @classmethod
    def validateUrl(cls, value: str | None) -> str | None:
        return validateAssetUrl(value)


class BodyImageOut(BaseModel):
    id: str
    index: int
    alt: str
    url: str
    caption: str
    """A standalone image renders as a figure; one inside a sentence stays inline."""
    standalone: bool
    sectionId: str
    sectionHeading: str


class BodyImageList(BaseModel):
    slug: str
    status: str
    editable: bool
    images: list[BodyImageOut]


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


class SubscriberCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=1, max_length=320)
    name: str = Field(default="", max_length=subscriberNameMaxLength)
    source: str = Field(default="", max_length=subscriberSourceMaxLength)

    @field_validator("email")
    @classmethod
    def validateEmail(cls, value: str) -> str:
        return validateSubscriberEmail(value)

    @field_validator("name", "source")
    @classmethod
    def trimStrings(cls, value: str) -> str:
        return value.strip()


class SubscriberUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=subscriberNameMaxLength)

    @field_validator("name")
    @classmethod
    def trimName(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("name cannot be blank")
        return trimmed


class SubscriberOut(BaseModel):
    email: str
    name: str = ""
    status: str
    createdUnix: float
    updatedUnix: float


class SubscriberIssued(SubscriberOut):
    token: str


class SubscriberAdmin(BaseModel):
    id: str
    email: str
    name: str = ""
    status: str
    clientIp: str = ""
    source: str = ""
    createdUnix: float
    updatedUnix: float


class SubscriberAdminList(BaseModel):
    total: int
    active: int
    subscribers: list[SubscriberAdmin]
