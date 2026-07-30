import type { GetStaticPaths, GetStaticProps } from "next";
import Head from "next/head";
import { useEffect, useState } from "react";

import { ArticleView } from "../../components/ArticleView";
import { SiteShell } from "../../components/SiteShell";
import { fetchArticle, fetchArticles, recordArticleView } from "../../lib/api";
import type { articleDetail } from "../../lib/types";

type articlePageProps = { article: articleDetail };

export const getStaticPaths: GetStaticPaths = async () => {
  try {
    const articles = await fetchArticles();
    return {
      paths: articles.map((article) => ({ params: { slug: article.slug } })),
      fallback: "blocking",
    };
  } catch (error) {
    console.warn("Article API was unavailable during the build; articles will be generated on first request.", error);
    return { paths: [], fallback: "blocking" };
  }
};

export const getStaticProps: GetStaticProps<articlePageProps, { slug: string }> = async ({ params }) => {
  if (!params?.slug) return { notFound: true, revalidate: 60 };

  try {
    const article = await fetchArticle(params.slug);
    return {
      props: { article },
      revalidate: 300,
    };
  } catch {
    return { notFound: true, revalidate: 60 };
  }
};

export default function ArticlePage({ article }: articlePageProps) {
  const [views, setViews] = useState<number | null>(null);
  const seo = article.seo;
  const metaTitle = seo?.metaTitle || `${article.title} — Jack Hales`;
  const metaDescription = seo?.metaDescription || article.summary;
  const socialImage = seo?.ogImageUrl || article.heroImage?.url || null;

  useEffect(() => {
    let active = true;

    recordArticleView(article.slug)
      .then((result) => {
        if (active) setViews(result.views);
      })
      .catch(() => {
        // Reading the article should still work if analytics is unavailable.
      });

    return () => {
      active = false;
    };
  }, [article.slug]);

  return (
    <SiteShell>
      <Head>
        <title>{metaTitle}</title>
        <meta name="description" content={metaDescription} />
        {seo?.keywords?.length ? <meta name="keywords" content={seo.keywords.join(", ")} /> : null}
        {seo?.canonicalUrl ? <link rel="canonical" href={seo.canonicalUrl} /> : null}
        {seo?.noIndex ? <meta name="robots" content="noindex, nofollow" /> : null}
        <meta property="og:type" content="article" />
        <meta property="og:title" content={seo?.metaTitle || article.title} />
        <meta property="og:description" content={metaDescription} />
        {socialImage ? <meta property="og:image" content={socialImage} /> : null}
        <meta name="twitter:card" content={socialImage ? "summary_large_image" : "summary"} />
        <meta property="article:published_time" content={article.publishedAt} />
      </Head>

      <ArticleView article={article} views={views} />
    </SiteShell>
  );
}
