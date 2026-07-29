import { Bold, Code2, Heading1, Italic, Link2, List, Quote, RotateCcw, Save, Send } from "lucide-react";
import { useMemo, useState } from "react";

import type { articleDetail, articleImage, articleSeo } from "../lib/types";
import { MarkdownContent } from "./MarkdownContent";

type articleFormProps = {
  article?: articleDetail;
  mode: "create" | "edit";
  onSubmit: (article: articlePayload) => Promise<void>;
  onCancel: () => void;
};

export type articlePayload = {
  title: string;
  slug: string;
  summary: string;
  bodyMarkdown: string;
  publishedAt: string;
  status: "draft" | "published";
  seo: articleSeo;
  heroImage: articleImage | null;
};

function optionalText(value: string): string | null {
  return value.trim() || null;
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function isoFromInput(value: string): string {
  return new Date(`${value}T00:00:00.000Z`).toISOString();
}

export function ArticleForm({ article, mode, onSubmit, onCancel }: articleFormProps) {
  const [title, setTitle] = useState(article?.title || "");
  const [slug, setSlug] = useState(article?.slug || "");
  const [automaticSlug, setAutomaticSlug] = useState(mode === "create" || !article?.slug);
  const [summary, setSummary] = useState(article?.summary || "");
  const [bodyMarkdown, setBodyMarkdown] = useState(article?.bodyMarkdown || "");
  const [publishedAt, setPublishedAt] = useState(article?.publishedAt.slice(0, 10) || new Date().toISOString().slice(0, 10));
  const [status, setStatus] = useState<"draft" | "published">(article?.status || "draft");
  const [metaTitle, setMetaTitle] = useState(article?.seo?.metaTitle || "");
  const [metaDescription, setMetaDescription] = useState(article?.seo?.metaDescription || "");
  const [canonicalUrl, setCanonicalUrl] = useState(article?.seo?.canonicalUrl || "");
  const [keywords, setKeywords] = useState((article?.seo?.keywords || []).join(", "));
  const [ogImageUrl, setOgImageUrl] = useState(article?.seo?.ogImageUrl || "");
  const [noIndex, setNoIndex] = useState(article?.seo?.noIndex || false);
  const [heroImageUrl, setHeroImageUrl] = useState(article?.heroImage?.url || "");
  const [heroImageAlt, setHeroImageAlt] = useState(article?.heroImage?.alt || "");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  const generatedSlug = useMemo(() => slugify(title), [title]);
  const computedSlug = automaticSlug ? generatedSlug : slug;
  const canSubmit = Boolean(title.trim() && computedSlug && publishedAt);

  function insertToken(before: string, after = "") {
    const textarea = document.querySelector<HTMLTextAreaElement>("#bodyMarkdown");
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = bodyMarkdown.slice(start, end);
    const next = `${bodyMarkdown.slice(0, start)}${before}${selected}${after}${bodyMarkdown.slice(end)}`;
    setBodyMarkdown(next);
    requestAnimationFrame(() => textarea.focus());
  }

  function setCustomSlugValue(value: string) {
    setAutomaticSlug(false);
    setSlug(slugify(value));
  }

  function resetSlug() {
    setSlug("");
    setAutomaticSlug(true);
  }

  async function submit(nextStatus?: "draft" | "published") {
    if (!canSubmit) {
      setFormError("Add a title so the article has a valid slug before saving.");
      return;
    }

    setSaving(true);
    setFormError("");
    try {
      const resolvedStatus = nextStatus || status;
      await onSubmit({
        title: title.trim(),
        slug: computedSlug,
        summary: summary.trim(),
        bodyMarkdown,
        publishedAt: isoFromInput(publishedAt),
        status: resolvedStatus,
        seo: {
          metaTitle: optionalText(metaTitle),
          metaDescription: optionalText(metaDescription),
          canonicalUrl: optionalText(canonicalUrl),
          keywords: keywords.split(",").map((keyword) => keyword.trim()).filter(Boolean),
          ogImageUrl: optionalText(ogImageUrl),
          noIndex,
        },
        heroImage: heroImageUrl.trim() ? { url: heroImageUrl.trim(), alt: heroImageAlt.trim() } : null,
      });
      setStatus(resolvedStatus);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Unable to save the article.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="article-editor">
      <div className="article-editor-intro">
        <div><p className="eyebrow">{mode === "create" ? "Create article" : "Article details"}</p><h2>{mode === "create" ? "Start with the essentials." : "Update the article."}</h2></div>
        <span className={`article-status article-status-${status}`}>{status}</span>
      </div>

      <div className="editor-fields-grid">
        <label className="editor-field editor-field-wide">
          <span>Title</span>
          <input value={title} placeholder="A clear, specific article title" onChange={(event) => setTitle(event.target.value)} />
        </label>

        <label className="editor-field editor-field-wide">
          <span className="editor-label-row"><span>Slug</span><small>{automaticSlug ? "Generated from the title" : "Custom slug"}</small></span>
          <div className="slug-field">
            <span>/article/</span>
            <input value={computedSlug} placeholder="generated-from-the-title" onChange={(event) => setCustomSlugValue(event.target.value)} />
            {!automaticSlug ? <button type="button" title="Reset to automatic slug" onClick={resetSlug}><RotateCcw size={15} /></button> : null}
          </div>
        </label>

        <label className="editor-field editor-field-wide">
          <span className="editor-label-row"><span>Summary</span><small>{summary.length}/500</small></span>
          <textarea maxLength={500} value={summary} placeholder="A concise description used on article cards and in search results." onChange={(event) => setSummary(event.target.value)} />
        </label>

        <label className="editor-field">
          <span>Publication date</span>
          <input type="date" value={publishedAt} onChange={(event) => setPublishedAt(event.target.value)} />
        </label>

        <label className="editor-field">
          <span>Status</span>
          <select value={status} onChange={(event) => setStatus(event.target.value as "draft" | "published")}>
            <option value="draft">Draft</option>
            <option value="published">Published</option>
          </select>
        </label>
      </div>

      <details className="editor-seo" open={Boolean(metaTitle || metaDescription || canonicalUrl || keywords || ogImageUrl || heroImageUrl || noIndex)}>
        <summary>SEO and images</summary>
        <div className="editor-fields-grid">
          <label className="editor-field">
            <span className="editor-label-row"><span>Meta title</span><small>Falls back to the title</small></span>
            <input value={metaTitle} maxLength={180} placeholder={title || "Article title"} onChange={(event) => setMetaTitle(event.target.value)} />
          </label>

          <label className="editor-field">
            <span className="editor-label-row"><span>Canonical URL</span><small>Optional</small></span>
            <input value={canonicalUrl} maxLength={500} placeholder="https://jackhales.com/article/…" onChange={(event) => setCanonicalUrl(event.target.value)} />
          </label>

          <label className="editor-field editor-field-wide">
            <span className="editor-label-row"><span>Meta description</span><small>{metaDescription.length}/320 — falls back to the summary</small></span>
            <textarea maxLength={320} value={metaDescription} placeholder="How this article should read in search results." onChange={(event) => setMetaDescription(event.target.value)} />
          </label>

          <label className="editor-field editor-field-wide">
            <span className="editor-label-row"><span>Keywords</span><small>Comma separated</small></span>
            <input value={keywords} placeholder="research, engineering, travel" onChange={(event) => setKeywords(event.target.value)} />
          </label>

          <label className="editor-field">
            <span>Social image URL</span>
            <input value={ogImageUrl} maxLength={500} placeholder="https://jackhales.com/og/article.png" onChange={(event) => setOgImageUrl(event.target.value)} />
          </label>

          <label className="editor-field">
            <span>Hero image URL</span>
            <input value={heroImageUrl} maxLength={500} placeholder="/images/hero.png" onChange={(event) => setHeroImageUrl(event.target.value)} />
          </label>

          <label className="editor-field">
            <span>Hero image alt text</span>
            <input value={heroImageAlt} maxLength={300} placeholder="What the image shows" onChange={(event) => setHeroImageAlt(event.target.value)} />
          </label>

          <label className="editor-field editor-checkbox">
            <input type="checkbox" checked={noIndex} onChange={(event) => setNoIndex(event.target.checked)} />
            <span>Ask search engines not to index this article</span>
          </label>
        </div>
      </details>

      <div className="editor-content-heading">
        <div><p className="eyebrow">Article content</p><h2>Write and preview together.</h2></div>
        <div className="editor-toolbar" aria-label="Markdown formatting">
          <button type="button" title="Heading" onClick={() => insertToken("\n## ")}><Heading1 size={17} /></button>
          <button type="button" title="Bold" onClick={() => insertToken("**", "**")}><Bold size={17} /></button>
          <button type="button" title="Italic" onClick={() => insertToken("_", "_")}><Italic size={17} /></button>
          <button type="button" title="Link" onClick={() => insertToken("[", "](https://)")}><Link2 size={17} /></button>
          <button type="button" title="List" onClick={() => insertToken("\n- ")}><List size={17} /></button>
          <button type="button" title="Quote" onClick={() => insertToken("\n> ")}><Quote size={17} /></button>
          <button type="button" title="HTML embed" onClick={() => insertToken("\n<div>\n", "\n</div>\n")}><Code2 size={17} /></button>
        </div>
      </div>

      <div className="editor-content-grid">
        <label className="editor-panel">
          <span>Markdown</span>
          <textarea id="bodyMarkdown" value={bodyMarkdown} placeholder="Start writing in Markdown…" onChange={(event) => setBodyMarkdown(event.target.value)} />
        </label>
        <div className="editor-panel">
          <span>Live preview</span>
          <div className="article-editor-preview">
            {bodyMarkdown ? <MarkdownContent markdown={bodyMarkdown} /> : <div className="editor-preview-empty"><FilePreviewIcon /><p>Your formatted article will appear here.</p></div>}
          </div>
        </div>
      </div>

      {formError ? <div className="admin-error editor-error">{formError}</div> : null}

      <div className="editor-actions">
        <button type="button" className="button button-outline" disabled={saving} onClick={onCancel}>Cancel</button>
        <div>
          <button type="button" className="button button-outline" disabled={saving || !canSubmit} onClick={() => submit("draft")}><Save size={16} /> Save draft</button>
          <button type="button" className="button button-dark" disabled={saving || !canSubmit} onClick={() => submit("published")}><Send size={16} /> {saving ? "Saving…" : "Publish"}</button>
        </div>
      </div>
    </div>
  );
}

function FilePreviewIcon() {
  return <Code2 size={24} />;
}
