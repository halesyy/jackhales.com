import { ArrowUpRight, BookOpen, Clock3, Sparkles } from "lucide-react";
import Head from "next/head";
import Link from "next/link";

import { Reveal, Stagger, StaggerItem } from "../components/Motion";
import { SiteShell } from "../components/SiteShell";
import { formatDate } from "../lib/date";
import { fetchArticles } from "../lib/api";
import type { articleSummary } from "../lib/types";

type articlesPageProps = { articles: articleSummary[] };

export async function getServerSideProps() {
  const articles = await fetchArticles();
  return { props: { articles } };
}

function articleTheme(title: string): string {
  const value = title.toLowerCase();
  if (value.includes("prime") || value.includes("topology")) return "Research";
  if (value.includes("ai") || value.includes("language") || value.includes("classifier")) return "Applied AI";
  if (value.includes("property") || value.includes("shopify")) return "Data notes";
  return "Thinking aloud";
}

export default function ArticlesPage({ articles }: articlesPageProps) {
  const [featured, ...rest] = articles;

  return (
    <SiteShell>
      <Head>
        <title>Writing — Jack Hales</title>
        <meta name="description" content="Research journals, technical notes and ideas by Australian software engineer Jack Hales." />
      </Head>

      <Reveal className="page-hero page-hero-row">
        <div>
          <p className="eyebrow">Writing & research</p>
          <h1 className="display-title">Notes from the <span className="accent">workbench.</span></h1>
        </div>
        <div className="page-side-lead">
          <p className="lead">Research journals, technical field notes and unfinished ideas. Written to clarify the thinking, not just present the answer.</p>
          <Link href="/ai-assisted" className="side-lead-link"><Sparkles size={14} /> Why some of these say AI-assisted <ArrowUpRight size={14} /></Link>
        </div>
      </Reveal>

      {featured ? (
        <Reveal>
          <Link href={`/article/${featured.slug}`} className="featured-article card card-interactive">
            <div className="featured-art"><span>{articleTheme(featured.title)}</span><BookOpen size={54} /></div>
            <div className="featured-copy">
              <div className="article-meta">
                <span>{articleTheme(featured.title)}</span>
                <span><Clock3 size={13} /> {formatDate(featured.publishedAt)}</span>
                {featured.aiAssisted ? <span className="article-meta-ai"><Sparkles size={13} /> AI-assisted</span> : null}
              </div>
              <h2>{featured.title}</h2>
              <p>{featured.summary}</p>
              <strong>Read article <ArrowUpRight size={16} /></strong>
            </div>
          </Link>
        </Reveal>
      ) : null}

      <section className="section-block articles-section">
        <Reveal className="section-heading">
          <div><p className="eyebrow">The archive</p><h2>More ideas and explorations.</h2></div>
          <p>{articles.length} entries across software, data, probability and the spaces between them.</p>
        </Reveal>
        <Stagger className="articles-grid">
          {rest.map((article, index) => (
            <StaggerItem key={article.slug}>
              <Link href={`/article/${article.slug}`} className={`article-card card card-interactive article-tone-${index % 3}`}>
                <div className="article-card-top">
                  <span className="tag">{articleTheme(article.title)}</span>
                  {article.aiAssisted ? <span className="tag tag-ai"><Sparkles size={12} /> AI-assisted</span> : null}
                  <ArrowUpRight size={17} />
                </div>
                <h2>{article.title}</h2>
                <p>{article.summary}</p>
                <time>{formatDate(article.publishedAt)}</time>
              </Link>
            </StaggerItem>
          ))}
        </Stagger>
      </section>
    </SiteShell>
  );
}
