import type { articleRenderable } from "./types";

/**
 * The handoff between the editor and the preview page.
 *
 * The preview opens in its own tab, so the draft travels through localStorage
 * rather than the URL: it is far too big for a query string, and an unpublished
 * article has no business in browser history or a server log. Writing a new
 * snapshot also fires a `storage` event, which is how an already-open preview
 * tab refreshes itself when Preview is pressed again.
 */

export const previewDraftKey = "jackhales.previewDraft.v1";
export const previewPath = "/admin/preview";

export type previewDraft = articleRenderable & {
  status: "draft" | "published";
  savedUnix: number;
};

export function savePreviewDraft(article: articleRenderable, status: "draft" | "published"): boolean {
  try {
    const draft: previewDraft = { ...article, status, savedUnix: Date.now() / 1000 };
    window.localStorage.setItem(previewDraftKey, JSON.stringify(draft));
    return true;
  } catch {
    // Private browsing and a full quota both land here; the caller says so.
    return false;
  }
}

export function readPreviewDraft(): previewDraft | null {
  try {
    const stored = window.localStorage.getItem(previewDraftKey);
    if (!stored) return null;
    const draft = JSON.parse(stored) as previewDraft;
    return typeof draft?.bodyMarkdown === "string" ? draft : null;
  } catch {
    return null;
  }
}
