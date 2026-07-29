import type { articleDetail, articleSummary, articleViewCount, subscriber, subscriberIssued } from "./types";

export function apiBaseUrl(): string {
  if (typeof window === "undefined") {
    return process.env.INTERNAL_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";
  }
  return process.env.NEXT_PUBLIC_API_BASE_URL || "/api";
}

/** A failed API response, carrying the HTTP status so callers can branch on it (422 vs 429 vs everything else) without string-matching the message. */
export class apiError extends Error {
  status: number;

  constructor(status: number) {
    super(`API request failed: ${status}`);
    this.name = "apiError";
    this.status = status;
  }
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new apiError(response.status);
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

export async function subscribeToUpdates(payload: { email: string; name?: string; source?: string }): Promise<subscriberIssued> {
  const response = await fetchApi("/subscribers", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<subscriberIssued>(response);
}

export async function fetchSubscriber(token: string): Promise<subscriber> {
  const response = await fetchApi("/subscribers/me", {
    headers: { "X-Subscriber-Token": token },
  });
  return parseJson<subscriber>(response);
}

export async function updateSubscriberName(token: string, name: string): Promise<subscriber> {
  const response = await fetchApi("/subscribers/me", {
    method: "PATCH",
    headers: { "content-type": "application/json", "X-Subscriber-Token": token },
    body: JSON.stringify({ name }),
  });
  return parseJson<subscriber>(response);
}

export async function unsubscribe(token: string): Promise<{ unsubscribed: true }> {
  const response = await fetchApi("/subscribers/me", {
    method: "DELETE",
    headers: { "X-Subscriber-Token": token },
  });
  return parseJson<{ unsubscribed: true }>(response);
}
