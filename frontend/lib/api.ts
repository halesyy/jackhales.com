import type { articleDetail, articleSummary, articleViewCount, imageAsset, imageAssetList, subscriber, subscriberIssued } from "./types";

export function apiBaseUrl(): string {
  if (typeof window === "undefined") {
    return process.env.INTERNAL_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";
  }
  return process.env.NEXT_PUBLIC_API_BASE_URL || "/api";
}

/** A failed API response, carrying the HTTP status so callers can branch on it (422 vs 429 vs everything else) without string-matching the message. */
export class apiError extends Error {
  status: number;

  constructor(status: number, detail = "") {
    super(detail || `API request failed: ${status}`);
    this.name = "apiError";
    this.status = status;
  }
}

/** The API explains its refusals in `detail`; showing that beats showing a bare status code. */
async function readErrorDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && typeof body.detail[0]?.msg === "string") return body.detail[0].msg as string;
  } catch {
    // A non-JSON error body just leaves the status to speak for itself.
  }
  return "";
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new apiError(response.status, await readErrorDetail(response));
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

export async function fetchImageLibrary(): Promise<imageAssetList> {
  return adminFetch<imageAssetList>("/admin/images");
}

/** Sends the file itself as the request body — the editor already holds the bytes after a paste. */
export async function uploadImage(file: Blob, filename: string, alt = ""): Promise<imageAsset> {
  const headers: Record<string, string> = {
    "content-type": file.type || "application/octet-stream",
    "X-Image-Filename": asciiHeader(filename),
  };
  if (alt.trim()) headers["X-Image-Alt"] = asciiHeader(alt);

  const response = await fetchApi("/admin/images", { method: "POST", credentials: "include", headers, body: file });
  return parseJson<imageAsset>(response);
}

export async function updateImageAlt(imageId: string, alt: string): Promise<imageAsset> {
  return adminFetch<imageAsset>(`/admin/images/${imageId}`, { method: "PATCH", body: JSON.stringify({ alt }) });
}

export async function deleteImage(imageId: string): Promise<{ deleted: true }> {
  return adminFetch<{ deleted: true }>(`/admin/images/${imageId}`, { method: "DELETE" });
}

/** Header values must be latin-1, so a filename or alt text with an emoji cannot be sent verbatim. */
function asciiHeader(value: string): string {
  return value.replace(/[^\x20-\x7e]+/g, "").trim().slice(0, 300);
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
