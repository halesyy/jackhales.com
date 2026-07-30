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

/** A stored image. The id is a digest of the bytes, so `url` never changes meaning and is cached forever. */
export type imageAsset = {
  id: string;
  url: string;
  contentType: string;
  width: number;
  height: number;
  byteSize: number;
  alt: string;
  filename: string;
  createdUnix: number;
  updatedUnix: number;
};

export type imageAssetList = {
  total: number;
  bytesUsed: number;
  /** What is left of the library's storage ceiling, in bytes. */
  bytesAvailable: number;
  images: imageAsset[];
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

/** A newsletter subscriber, as seen by the subscriber themself via /subscribers and /subscribers/me. */
export type subscriber = {
  email: string;
  /** Empty string, not null, when the subscriber hasn't given a name. */
  name: string;
  status: string;
  /** Unix seconds (a float, not milliseconds and not an ISO string) — render with formatUnixDate. */
  createdUnix: number;
  updatedUnix: number;
};

/** Returned once, at signup. The token authenticates later /subscribers/me requests; subscribing again with the same address rotates it, which is how a lost one is replaced. */
export type subscriberIssued = subscriber & { token: string };

/** A subscriber as seen from the admin listing — includes fields the subscriber themself never sees. */
export type adminSubscriber = {
  id: string;
  email: string;
  /** Empty string, not null, when the subscriber hasn't given a name. */
  name: string;
  status: string;
  /** IP address the signup request came from. */
  clientIp: string;
  /** The page path sent at signup (e.g. "/", "/articles/some-post"). Empty string, not null, if none was sent. */
  source: string;
  createdUnix: number;
  updatedUnix: number;
};

export type adminSubscriberList = {
  total: number;
  active: number;
  subscribers: adminSubscriber[];
};
