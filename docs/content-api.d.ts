/**
 * Type definitions for the Jack Hales draft content API.
 *
 * Base URL: https://api.jackhales.com/api
 * Auth:     Authorization: Bearer <key>   (or X-API-Key: <key>)
 *
 * An API key can read everything and edit drafts. It can never publish, never
 * change a published article, and never delete an article.
 */

export type ArticleStatus = "draft" | "published";

export interface ArticleSeo {
  /** Falls back to the article title when null. */
  metaTitle: string | null;
  /** Falls back to the article summary when null. */
  metaDescription: string | null;
  canonicalUrl: string | null;
  keywords: string[];
  ogImageUrl: string | null;
  noIndex: boolean;
}

export interface ArticleImage {
  /** Must start with https://, http:// or /. */
  url: string;
  alt: string;
  caption?: string;
}

export interface ArticleSummary {
  id: string;
  title: string;
  slug: string;
  summary: string;
  /** ISO 8601 timestamp. */
  publishedAt: string;
  status: ArticleStatus;
  /**
   * Set to true automatically by every write made with an API key, and rendered
   * as the AI-assisted badge. A key cannot set or clear it; only the admin can.
   */
  aiAssisted: boolean;
  updatedAt: string;
}

export interface Article extends ArticleSummary {
  bodyMarkdown: string;
  seo: ArticleSeo;
  heroImage: ArticleImage | null;
  sourceUrl: string | null;
  createdAt: string;
}

/** One addressable region of the body, split on ATX headings outside code fences. */
export interface ArticleSection {
  /** Heading anchor, `-2`/`-3` suffixed when a heading repeats. Text before the first heading is `preamble`. */
  id: string;
  index: number;
  /** 1–6 for a heading, 0 for the preamble. */
  level: number;
  heading: string;
  body: string;
  characters: number;
  words: number;
}

export interface ArticleSectionList {
  slug: string;
  status: ArticleStatus;
  /** False for published articles: every write route will answer 409. */
  editable: boolean;
  sections: ArticleSection[];
}

export interface ContentIdentity {
  authenticated: true;
  scope: "articles:draft";
  label: string;
  hint: string;
  canPublish: false;
  permissions: string[];
  restrictions: string[];
}

/**
 * POST /content/articles — the created article always comes back as a draft.
 * Sending `status`, `publish`, `published` or `publishedState` is a 422.
 */
export interface DraftCreate {
  title: string;
  /** Derived from the title when omitted. */
  slug?: string;
  summary?: string;
  bodyMarkdown?: string;
  publishedAt?: string;
  seo?: Partial<ArticleSeo>;
  heroImage?: ArticleImage;
}

/** PATCH /content/articles/{slug} — at least one field is required. */
export interface DraftUpdate {
  title?: string;
  slug?: string;
  summary?: string;
  bodyMarkdown?: string;
  publishedAt?: string;
  seo?: Partial<ArticleSeo>;
  heroImage?: ArticleImage;
  /** Removes the hero image. */
  clearHeroImage?: boolean;
}

/** PUT /content/articles/{slug}/body */
export interface DraftBody {
  bodyMarkdown: string;
}

/** PUT /content/articles/{slug}/sections/{sectionId} — provide a heading, a body, or both. */
export interface SectionUpdate {
  heading?: string;
  body?: string;
}

/** POST /content/articles/{slug}/sections — provide exactly one of after or before. */
export interface SectionInsert {
  heading: string;
  body?: string;
  /** 1–6, defaults to 2. */
  level?: number;
  after?: string;
  before?: string;
}

/** POST /content/articles/{slug}/body/replace */
export interface BodyReplace {
  find: string;
  replace?: string;
  /** Required when `find` matches more than once; the edit is refused if the count differs. */
  expectedCount?: number;
}

/** FastAPI error shape. */
export interface ApiError {
  detail: string;
}

export interface ContentApi {
  "GET /content/whoami": { response: ContentIdentity };
  "GET /content/articles": { query?: { status?: ArticleStatus }; response: ArticleSummary[] };
  "GET /content/articles/{slug}": { response: Article };
  "POST /content/articles": { body: DraftCreate; response: Article };
  "PATCH /content/articles/{slug}": { body: DraftUpdate; response: Article };
  "PUT /content/articles/{slug}/body": { body: DraftBody; response: Article };
  "POST /content/articles/{slug}/body/replace": { body: BodyReplace; response: Article };
  "GET /content/articles/{slug}/sections": { response: ArticleSectionList };
  "PUT /content/articles/{slug}/sections/{sectionId}": { body: SectionUpdate; response: Article };
  "POST /content/articles/{slug}/sections": { body: SectionInsert; response: Article };
  "DELETE /content/articles/{slug}/sections/{sectionId}": { response: Article };
}
