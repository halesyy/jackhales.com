from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class AdminCredentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=1024)

    @field_validator("email")
    @classmethod
    def normalizeEmail(cls, value: str) -> str:
        return value.strip().lower()


class ArticleBase(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    slug: str = Field(min_length=1, max_length=220)
    summary: str = Field(default="", max_length=500)
    bodyMarkdown: str = Field(default="")
    publishedAt: datetime
    status: str = Field(default="draft", pattern="^(draft|published)$")

    @field_validator("slug")
    @classmethod
    def validateSlug(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized.replace("-", "").replace("_", "").isalnum():
            raise ValueError("slug may contain letters, numbers, dashes, and underscores only")
        return normalized


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    slug: str | None = Field(default=None, min_length=1, max_length=220)
    summary: str | None = Field(default=None, max_length=500)
    bodyMarkdown: str | None = None
    publishedAt: datetime | None = None
    status: str | None = Field(default=None, pattern="^(draft|published)$")

    @field_validator("slug")
    @classmethod
    def validateSlug(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if not normalized.replace("-", "").replace("_", "").isalnum():
            raise ValueError("slug may contain letters, numbers, dashes, and underscores only")
        return normalized


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
