import type { articleDetail, articleSummary, articleViewCount } from "./types";

export function apiBaseUrl(): string {
  if (typeof window === "undefined") {
    return process.env.INTERNAL_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";
  }
  return process.env.NEXT_PUBLIC_API_BASE_URL || "/api";
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function fetchApi(path: string, init?: RequestInit): Promise<Response> {
  const attempts = typeof window === "undefined" ? 4 : 1;
  let lastError: unknown;

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      const response = await fetch(`${apiBaseUrl()}${path}`, init);
      if (response.status < 500 || attempt === attempts) return response;
      lastError = new Error(`API request failed: ${response.status}`);
    } catch (error) {
      lastError = error;
      if (attempt === attempts) throw error;
    }

    await new Promise((resolve) => setTimeout(resolve, attempt * 250));
  }

  throw lastError instanceof Error ? lastError : new Error("API request failed");
}

export async function fetchArticles(): Promise<articleSummary[]> {
  const response = await fetchApi("/articles", { credentials: "include" });
  return parseJson<articleSummary[]>(response);
}

export async function fetchArticle(slug: string): Promise<articleDetail> {
  const response = await fetchApi(`/articles/${slug}`, { credentials: "include" });
  return parseJson<articleDetail>(response);
}

export async function recordArticleView(slug: string): Promise<articleViewCount> {
  const response = await fetchApi(`/articles/${encodeURIComponent(slug)}/views`, {
    method: "POST",
    credentials: "include",
  });
  return parseJson<articleViewCount>(response);
}

export async function adminFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetchApi(path, {
    credentials: "include",
    headers: { "content-type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  return parseJson<T>(response);
}
