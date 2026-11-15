import type { articleSummary } from "./types";

export type readNextArticle = Pick<articleSummary, "slug" | "title" | "summary">;

/**
 * The one article to suggest after this one.
 *
 * Articles have no tags, so we walk back in time: the article published just
 * before this one, and for the oldest article, the newest. It is never the
 * article itself, and null only when there is no other published article.
 */
export function pickReadNext(articles: articleSummary[], slug: string): readNextArticle | null {
  const ordered = [...articles]
    .filter((article) => article.status === "published")
    .sort((a, b) => b.publishedAt.localeCompare(a.publishedAt));
  const others = ordered.filter((article) => article.slug !== slug);
  if (others.length === 0) return null;

  const index = ordered.findIndex((article) => article.slug === slug);
  const older = index >= 0 ? ordered.slice(index + 1).find((article) => article.slug !== slug) : undefined;
  const pick = older ?? others[0];
  return { slug: pick.slug, title: pick.title, summary: pick.summary };
}
