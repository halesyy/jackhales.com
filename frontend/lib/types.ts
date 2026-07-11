export type articleStatus = "draft" | "published";

export type articleSummary = {
  id: string;
  title: string;
  slug: string;
  summary: string;
  publishedAt: string;
  status: articleStatus;
  updatedAt: string;
};

export type articleDetail = articleSummary & {
  bodyMarkdown: string;
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
