import { ArrowLeft, CalendarDays, Eye, UserRound } from "lucide-react";
import Link from "next/link";

import { formatDate } from "../lib/date";
import { imageDimensionsFrom } from "../lib/images";
import type { articleRenderable } from "../lib/types";
import { AiAssistedBadge } from "./AiAssistedBadge";
import { MarkdownContent } from "./MarkdownContent";
import { Reveal } from "./Motion";

type articleViewProps = {
  article: articleRenderable;
  /** A count, `null` while it loads, or omitted entirely where views do not apply. */
  views?: number | null;
};

/**
 * An article, exactly as a reader sees it.
 *
 * The published page and the admin preview both render through here, so a draft
 * cannot look one way in the editor and another way once it is live. Anything
 * that differs between the two belongs in the page around this, not inside it.
 */
export function ArticleView({ article, views }: articleViewProps) {
  const heroSize = article.heroImage ? imageDimensionsFrom(article.heroImage.url) : null;

  return (
    <>
      <Reveal className="article-hero">
        <Link href="/articles" className="back-link"><ArrowLeft size={15} /> All writing</Link>
        <p className="eyebrow">Research &amp; writing</p>
        <h1>{article.title || "Untitled article"}</h1>
        {article.summary ? <p className="article-deck">{article.summary}</p> : null}
        <div className="article-byline">
          <span><UserRound size={15} /> Jack Hales</span>
          <span><CalendarDays size={15} /> {formatDate(article.publishedAt)}</span>
          {views !== undefined ? (
            <span aria-live="polite">
              <Eye size={15} /> {views === null ? "Loading views" : `${views.toLocaleString()} ${views === 1 ? "view" : "views"}`}
            </span>
          ) : null}
          {article.aiAssisted ? <AiAssistedBadge /> : null}
        </div>
      </Reveal>

      {article.heroImage?.url ? (
        <Reveal className="article-hero-image" delay={0.05} viewportAmount="some">
          {/* Hero images come from the article record and can be any external host. */}
          <img
            src={article.heroImage.url}
            alt={article.heroImage.alt}
            width={heroSize?.width}
            height={heroSize?.height}
            loading="lazy"
          />
          {article.heroImage.caption ? <figcaption>{article.heroImage.caption}</figcaption> : null}
        </Reveal>
      ) : null}

      <Reveal className="article-paper card" delay={0.1} viewportAmount="some">
        <MarkdownContent markdown={article.bodyMarkdown} />
      </Reveal>
    </>
  );
}
