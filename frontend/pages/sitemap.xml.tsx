import type { GetServerSideProps } from "next";

import { apiBaseUrl } from "../lib/api";

export const getServerSideProps: GetServerSideProps = async ({ res }) => {
  const response = await fetch(`${apiBaseUrl()}/sitemap`);
  if (!response.ok) {
    throw new Error(`Sitemap API request failed: ${response.status}`);
  }

  res.setHeader("content-type", "application/xml");
  res.setHeader("cache-control", response.headers.get("cache-control") || "public, max-age=300");
  res.write(await response.text());
  res.end();
  return { props: {} };
};

export default function Sitemap() {
  return null;
}
