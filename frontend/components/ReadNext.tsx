import { ArrowRight } from "lucide-react";
import Link from "next/link";

import type { readNextArticle } from "../lib/readNext";
import { Reveal } from "./Motion";

/** One article to read after this one: a title, its one-line summary, and nothing else. */
export function ReadNext({ article }: { article: readNextArticle }) {
  return (
    <Reveal className="read-next" viewportAmount="some">
      <Link href={`/article/${article.slug}`} className="read-next-link card card-interactive">
        <p className="eyebrow">Read next</p>
        <h2>{article.title}</h2>
        {article.summary ? <p className="read-next-summary">{article.summary}</p> : null}
        <span className="read-next-go">Read it <ArrowRight size={15} /></span>
      </Link>
    </Reveal>
  );
}
