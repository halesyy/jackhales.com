import type { GetServerSideProps } from "next";

import { fetchArticles } from "../lib/api";
import type { articleSummary } from "../lib/types";

const SITE_URL = "https://jackhales.com";

function oneLine(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

function articleLines(articles: articleSummary[]): string[] {
  return [...articles]
    .sort((left, right) => Date.parse(right.publishedAt) - Date.parse(left.publishedAt))
    .map((article) => {
      const title = oneLine(article.title);
      const summary = oneLine(article.summary);
      const published = article.publishedAt.slice(0, 10);
      const description = summary || "A research note or working idea from Jack Hales.";
      const assisted = article.aiAssisted ? " (AI-assisted drafting; direction, research and conclusions are Jack's)" : "";

      return `- [${title}](${SITE_URL}/article/${encodeURIComponent(article.slug)}): ${description} (Published ${published})${assisted}`;
    });
}

export function renderLlmsTxt(articles: articleSummary[]): string {
  const writing = articleLines(articles);
  const latest = writing[0]
    ? `The most recently published entry is ${writing[0].replace(/^- /, "")}`
    : `Browse [Writing and research](${SITE_URL}/articles) for Jack's latest published work.`;

  return [
    "# Jack Hales — Australian AI Engineer",
    "",
    "> Jack Hales is an Australian AI engineer and systems thinker who builds reliable AI workflows, useful products, integrations, data platforms, and backend infrastructure. He turns ambiguous technical problems into dependable software designed for real-world use.",
    "",
    "This file is a concise guide to Jack's work, experience, interests, and writing. The canonical website is [jackhales.com](https://jackhales.com).",
    "",
    "## Overview",
    "",
    "- Based in Australia and focused primarily on AI engineering.",
    "- Works across LLM applications, agentic workflows, model-powered tools, product engineering, backend systems, data pipelines, integrations, and infrastructure.",
    "- Language-agnostic and pragmatic: tools and architecture are selected to fit the problem, operational constraints, and measurable outcome.",
    "- Interested in future AI engineering, product, research, and technical collaboration opportunities across Australia.",
    "",
    "## Current and recent work",
    "",
    "- [Pharma Portal](https://www.pharmaportal.com.au) (2021–present): an Australian pharmacy operations and reporting platform. Jack developed it end to end, including secure data transfer, dispensing and POS integrations, processing pipelines, reporting, and infrastructure.",
    "- [Shreem](https://www.shreem.au) (2024–2025): an Australian pharmacy marketplace built from client wireframes into a complete product with dynamic pricing, multi-supplier carts, stock synchronisation, supplier integrations, and Stripe payments.",
    `- Active technical interests include useful AI flows, intelligent tools, model evaluation, and [experimental prime-number research](${SITE_URL}/article/prime-number-research-2024).`,
    `- Latest writing: ${latest}`,
    "",
    "## Background and experience",
    "",
    "- End-to-end product delivery across product definition, interfaces, APIs, databases, data processing, integrations, deployment, and iteration.",
    "- Languages include JavaScript, TypeScript, Python, Rust, SQL, Bash, PHP, HTML, and CSS.",
    "- AI and data experience includes machine learning, model evaluation, Scikit-learn, Optuna, LangChain, OpenAI and Anthropic APIs, agent workflows, MCP, embeddings, and vector search.",
    "- Application and platform experience includes Next.js, React, Node.js, FastAPI, MongoDB, PostgreSQL, Docker, AWS, and GCP.",
    "- Integration experience spans Australian pharmacy and dispensing systems, logistics providers, Shopify, Salesforce, and Stripe.",
    "- Earlier systems experiments include Betfair browser automation and API integration, plus Python and Rust work on graph-based Binance arbitrage and live order-book data.",
    `- Read the fuller account on [Background and experience](${SITE_URL}/background-and-experience).`,
    "",
    "## Interests and passions",
    "",
    "- Applied AI, agentic systems, LLM tool design, model evaluation, and human–AI development workflows.",
    "- Mathematics, probability, uncertainty, complex systems, empirical research, and patterns in prime numbers.",
    "- Building software that connects difficult ideas to useful outcomes in real operations.",
    "- History, reading, music, travel, and bushwalking.",
    `- Travel writing includes [A software engineer's guide to exploring Oman](${SITE_URL}/software-engineers-guide-exploring-oman-top-travel-tips-itinerary).`,
    "",
    "## Future work in Australia",
    "",
    "Jack is interested in contributing to ambitious work in Australia as an AI engineer and technical product builder. Particularly relevant opportunities include applied AI systems, agentic workflows, data-intensive products, healthcare and pharmacy technology, operational software, integrations, infrastructure, and technically difficult research or prototyping. He is interested in work that creates durable value for Australian organisations and communities.",
    "",
    "- Contact: [me@jackhales.com](mailto:me@jackhales.com)",
    "- [LinkedIn](https://www.linkedin.com/in/jackhales/)",
    "- [GitHub](https://github.com/halesyy/)",
    "",
    "## Key pages",
    "",
    `- [Home](${SITE_URL}): concise introduction, capabilities, current interests, and selected work.`,
    `- [Background and experience](${SITE_URL}/background-and-experience): detailed product work, technical toolkit, integrations, experiments, and working philosophy.`,
    `- [Writing and research](${SITE_URL}/articles): the current article archive.`,
    `- [AI-assisted writing](${SITE_URL}/ai-assisted): what the AI-assisted badge means, why Jack writes this way, and the guardrails behind it.`,
    `- [Sitemap](${SITE_URL}/sitemap.xml): machine-readable index of public pages.`,
    "",
    "## How this writing is produced",
    "",
    `Some articles carry an [AI-assisted](${SITE_URL}/ai-assisted) badge. The badge means AI helped with drafting prose and breaking the content into sections. The questions, research, experiments, arguments, and conclusions are Jack's own, and every article is read and edited by him before it goes live.`,
    "",
    "- The badge is recorded automatically: any edit made through the site's scoped content API key marks that article as AI-assisted. The key cannot set or clear the flag itself.",
    "- That key can only work on drafts. It cannot publish, cannot modify an already-published article, and cannot delete anything. Jack is the only one who publishes.",
    "- Articles without the badge were written without AI assistance.",
    "- The reason is capacity rather than preference: Jack runs company building, prime-number research, and AI experimentation in parallel, and would otherwise leave most of the research unwritten.",
    "",
    "## Writing and further reading",
    "",
    "This section is generated from the website's currently published articles and updates automatically.",
    "",
    ...(writing.length
      ? writing
      : [`- [Writing and research](${SITE_URL}/articles): Browse the live archive for current articles and research notes.`]),
    "",
  ].join("\n");
}

export const getServerSideProps: GetServerSideProps = async ({ res }) => {
  let articles: articleSummary[] = [];

  try {
    articles = await fetchArticles();
  } catch (error) {
    console.warn("Article API was unavailable while generating llms.txt.", error);
  }

  res.setHeader("Content-Type", "text/plain; charset=utf-8");
  res.setHeader("Cache-Control", "public, s-maxage=300, stale-while-revalidate=86400");
  res.write(renderLlmsTxt(articles));
  res.end();

  return { props: {} };
};

export default function LlmsTxtPage() {
  return null;
}
