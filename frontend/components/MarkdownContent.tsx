import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import rehypeRaw from "rehype-raw";
import remarkGfm from "remark-gfm";

import { ArticleFigure } from "./ArticleFigure";
import { ArticleTable, ArticleTableCell, ArticleTableHead, ArticleTableHeaderCell, ArticleTableRow } from "./MarkdownTable";

type markdownContentProps = {
  markdown: string;
};

type paragraphNode = { children?: { type?: string; tagName?: string; value?: string }[] };

function localizeArticleLink(href?: string): string | undefined {
  if (!href) return href;
  return href.replace(/^https?:\/\/(?:www\.)?jackhales\.com(?=\/|$)/i, "") || "/";
}

/** An image on its own line is a figure, and a figure cannot legally live inside a paragraph. */
function isLoneImage(node: paragraphNode | undefined): boolean {
  const children = (node?.children || []).filter((child) => child.type !== "text" || child.value?.trim());
  return children.length === 1 && children[0].tagName === "img";
}

const components: Components = {
  a: ({ href, children, ...props }) => {
    const localizedHref = localizeArticleLink(href);
    const external = localizedHref?.startsWith("http");
    return (
      <a href={localizedHref} target={external ? "_blank" : undefined} rel={external ? "noreferrer" : undefined} {...props}>
        {children}
      </a>
    );
  },
  img: ({ src, alt, title }) => <ArticleFigure src={typeof src === "string" ? src : undefined} alt={alt} title={title} />,
  p: ({ node, children }) => (isLoneImage(node as paragraphNode) ? <>{children as ReactNode}</> : <p>{children}</p>),
  table: ArticleTable,
  thead: ArticleTableHead,
  tr: ArticleTableRow,
  th: ArticleTableHeaderCell,
  td: ArticleTableCell,
};

export function MarkdownContent({ markdown }: markdownContentProps) {
  return (
    <article className="prose">
      <ReactMarkdown components={components} remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
        {markdown}
      </ReactMarkdown>
    </article>
  );
}
