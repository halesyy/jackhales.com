export type articleStatus = "draft" | "published";

export type articleSeo = {
  metaTitle: string | null;
  metaDescription: string | null;
  canonicalUrl: string | null;
  keywords: string[];
  ogImageUrl: string | null;
  noIndex: boolean;
};

export type articleImage = {
  url: string;
  alt: string;
  caption?: string;
};

export type articleSummary = {
  id: string;
  title: string;
  slug: string;
  summary: string;
  publishedAt: string;
  status: articleStatus;
  /** Set automatically whenever the article is edited through an API key. */
  aiAssisted: boolean;
  updatedAt: string;
};

export type articleDetail = articleSummary & {
  bodyMarkdown: string;
  seo: articleSeo;
  heroImage: articleImage | null;
  sourceUrl?: string;
  createdAt: string;
};

export type adminStatus = {
  configured: boolean;
  authenticated: boolean;
  email: string;
};

export type articleViewCount = {
  views: number;
  counted?: boolean;
};

/** Metadata for the single active API key. The key itself is never returned again. */
export type apiKeyMetadata = {
  configured: boolean;
  scope: string;
  label: string;
  hint: string;
  createdAt: string | null;
  createdBy: string;
  lastUsedAt: string | null;
};

/** Returned once, at generation time. Generating a key supersedes the previous one. */
export type apiKeyIssued = apiKeyMetadata & { key: string };

/** A body section addressable by the content API without rewriting the whole article. */
export type articleSection = {
  id: string;
  index: number;
  level: number;
  heading: string;
  body: string;
  characters: number;
  words: number;
};

export type articleSectionList = {
  slug: string;
  status: articleStatus;
  editable: boolean;
  sections: articleSection[];
};

/** What an API key is allowed to do. Publishing and setting aiAssisted are deliberately absent. */
export type contentIdentity = {
  authenticated: boolean;
  scope: string;
  label: string;
  hint: string;
  canPublish: false;
  permissions: string[];
  restrictions: string[];
};
