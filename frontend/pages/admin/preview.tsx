import { ArrowLeft, Monitor, Smartphone, Tablet } from "lucide-react";
import Head from "next/head";
import Link from "next/link";
import { useEffect, useState } from "react";

import { ArticleView } from "../../components/ArticleView";
import { SiteShell } from "../../components/SiteShell";
import { previewDraftKey, readPreviewDraft, type previewDraft } from "../../lib/previewDraft";

/**
 * The draft, as a reader would see it.
 *
 * The article itself is rendered by the same `ArticleView` the published page
 * uses, inside an iframe rather than a narrowed `div`: the site's breakpoints
 * are viewport media queries, and only a real viewport makes them fire. A
 * width-constrained container would show desktop styling at phone width and
 * quietly lie about the thing most worth checking.
 */

type previewWidth = { label: string; width: number | null; icon: typeof Monitor };

const previewWidths: previewWidth[] = [
  { label: "Desktop", width: null, icon: Monitor },
  { label: "Tablet", width: 834, icon: Tablet },
  { label: "Phone", width: 390, icon: Smartphone },
];

/** Re-reads whenever the editor writes a new snapshot, so pressing Preview again refreshes this tab. */
function usePreviewDraft(): { draft: previewDraft | null; loaded: boolean } {
  const [draft, setDraft] = useState<previewDraft | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setDraft(readPreviewDraft());
    setLoaded(true);

    function onStorage(event: StorageEvent) {
      if (event.key === previewDraftKey || event.key === null) setDraft(readPreviewDraft());
    }

    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return { draft, loaded };
}

function capturedAgo(savedUnix: number): string {
  const minutes = Math.floor((Date.now() / 1000 - savedUnix) / 60);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours} hour${hours === 1 ? "" : "s"} ago`;
}

function PreviewMeta() {
  return (
    <Head>
      <title>Preview — Jack Hales</title>
      <meta name="robots" content="noindex, nofollow" />
    </Head>
  );
}

/** What the article looks like in a search result, from the same fallbacks the live page uses. */
function SearchPreview({ draft }: { draft: previewDraft }) {
  const title = draft.seo?.metaTitle || `${draft.title || "Untitled article"} — Jack Hales`;
  const description = draft.seo?.metaDescription || draft.summary;

  return (
    <details className="preview-seo">
      <summary>Search result</summary>
      <div className="preview-seo-card">
        <span className="preview-seo-url">jackhales.com › article › {draft.slug || "…"}</span>
        <strong>{title}</strong>
        <p>{description || "No summary or meta description yet — search engines will pick their own snippet."}</p>
        <div className="preview-seo-lengths">
          <span className={title.length > 60 ? "preview-seo-long" : undefined}>Title {title.length}/60</span>
          <span className={description.length > 160 ? "preview-seo-long" : undefined}>Description {description.length}/160</span>
          {draft.seo?.noIndex ? <span className="preview-seo-long">Set to noindex</span> : null}
        </div>
      </div>
    </details>
  );
}

export default function PreviewPage() {
  const { draft, loaded } = usePreviewDraft();
  const [width, setWidth] = useState<number | null>(null);
  const [framed, setFramed] = useState<boolean | null>(null);

  useEffect(() => {
    setFramed(new URLSearchParams(window.location.search).get("frame") === "1");
  }, []);

  // The draft lives in browser storage, so there is nothing to render until the
  // page is mounted. Both the server and the first client render agree on that,
  // which is what keeps hydration from mismatching.
  if (framed === null) return <PreviewMeta />;

  // Inside the iframe: nothing but the article, rendered exactly as it ships.
  if (framed) {
    return (
      <>
        <PreviewMeta />
        {draft ? (
          <SiteShell>
            <ArticleView article={draft} />
          </SiteShell>
        ) : (
          <div className="preview-empty card">
            <p className="eyebrow">Preview</p>
            <h1>Nothing to preview yet.</h1>
            <p>Choose <strong>Preview</strong> in the editor to send a draft here.</p>
          </div>
        )}
      </>
    );
  }

  if (loaded && !draft) {
    return (
      <>
        <PreviewMeta />
        <div className="preview-empty card">
          <p className="eyebrow">Preview</p>
          <h1>Nothing to preview yet.</h1>
          <p>Open an article in the editor and choose <strong>Preview</strong> to see it here.</p>
          <Link href="/admin" className="button button-dark"><ArrowLeft size={16} /> Publishing workspace</Link>
        </div>
      </>
    );
  }

  return (
    <>
      <PreviewMeta />
      <div className="preview-shell">
        <header className="preview-bar">
          <div className="preview-bar-title">
            <span className="preview-tag">Preview</span>
            <div>
              <strong>{draft?.title || "Untitled article"}</strong>
              <small>
                {draft ? `${draft.status === "published" ? "Published" : "Draft"} · captured ${capturedAgo(draft.savedUnix)}` : "Loading…"}
              </small>
            </div>
          </div>

          <div className="preview-widths" role="group" aria-label="Preview width">
            {previewWidths.map(({ label, width: value, icon: Icon }) => (
              <button
                key={label}
                type="button"
                title={value ? `${label} — ${value}px` : label}
                aria-pressed={width === value}
                className={width === value ? "is-active" : undefined}
                onClick={() => setWidth(value)}
              >
                <Icon size={15} /> {label}
              </button>
            ))}
          </div>

          <div className="preview-bar-actions">
            {draft ? <SearchPreview draft={draft} /> : null}
            <Link href="/admin" className="button button-outline"><ArrowLeft size={15} /> Editor</Link>
          </div>
        </header>

        <div className="preview-stage">
          <iframe
            title="Article preview"
            src="/admin/preview?frame=1"
            className="preview-frame"
            style={width ? { width: `${width}px` } : undefined}
          />
        </div>
      </div>
    </>
  );
}
