import { Bold, Code2, Eye, Heading1, ImageIcon, Italic, Link2, List, Quote, RotateCcw, Save, Send, Table } from "lucide-react";
import { useMemo, useRef, useState } from "react";

import { imageFilesFrom, imageMarkdown } from "../lib/images";
import { emptyTable, formatTable, replaceTable, tableAtOffset, type markdownTable } from "../lib/markdownTable";
import { previewPath, savePreviewDraft } from "../lib/previewDraft";
import type { articleDetail, articleImage, articleSeo, imageAsset } from "../lib/types";
import { useImageLibrary } from "../lib/useImageLibrary";
import { ArticleImageLibrary } from "./ArticleImageLibrary";
import { MarkdownContent } from "./MarkdownContent";
import { TableBuilder } from "./TableBuilder";

type articleFormProps = {
  article?: articleDetail;
  mode: "create" | "edit";
  onSubmit: (article: articlePayload) => Promise<void>;
  onCancel: () => void;
};

type tableEdit = { table: markdownTable; mode: "insert" | "edit"; offset: number };

export type articlePayload = {
  title: string;
  slug: string;
  summary: string;
  bodyMarkdown: string;
  publishedAt: string;
  status: "draft" | "published";
  aiAssisted: boolean;
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
  const [aiAssisted, setAiAssisted] = useState(article?.aiAssisted || false);
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
  const [editingTable, setEditingTable] = useState<tableEdit | null>(null);

  const bodyRef = useRef<HTMLTextAreaElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const previewWindow = useRef<Window | null>(null);
  const library = useImageLibrary(true);

  const generatedSlug = useMemo(() => slugify(title), [title]);
  const computedSlug = automaticSlug ? generatedSlug : slug;
  const canSubmit = Boolean(title.trim() && computedSlug && publishedAt);

  function focusBody(caret?: number) {
    requestAnimationFrame(() => {
      const textarea = bodyRef.current;
      if (!textarea) return;
      textarea.focus();
      if (caret !== undefined) textarea.setSelectionRange(caret, caret);
    });
  }

  function insertToken(before: string, after = "") {
    const textarea = bodyRef.current;
    if (!textarea) return;
    const { selectionStart: start, selectionEnd: end } = textarea;
    const selected = bodyMarkdown.slice(start, end);
    setBodyMarkdown(`${bodyMarkdown.slice(0, start)}${before}${selected}${after}${bodyMarkdown.slice(end)}`);
    focusBody(start + before.length + selected.length);
  }

  /** Drop a block on its own lines, keeping one blank line either side of it. */
  function insertBlock(block: string, offset = bodyRef.current?.selectionStart ?? bodyMarkdown.length) {
    const at = Math.min(Math.max(offset, 0), bodyMarkdown.length);
    const before = bodyMarkdown.slice(0, at).replace(/\n*$/, "");
    const after = bodyMarkdown.slice(at).replace(/^\n*/, "");
    const lead = before ? `${before}\n\n` : "";
    const next = `${lead}${block}${after ? `\n\n${after}` : "\n"}`;
    setBodyMarkdown(next);
    focusBody(lead.length + block.length);
  }

  async function uploadAndInsert(files: File[]) {
    const offset = bodyRef.current?.selectionStart ?? bodyMarkdown.length;
    const stored = await library.uploadFiles(files);
    if (!stored.length) return;
    insertBlock(stored.map((image) => imageMarkdown(image.url, image.alt)).join("\n\n"), offset);
  }

  function browseForImages() {
    fileInput.current?.click();
  }

  function useAsHero(image: imageAsset) {
    setHeroImageUrl(image.url);
    if (image.alt) setHeroImageAlt(image.alt);
  }

  /** Opens the grid on the table under the caret, or on a fresh one when there is none. */
  function openTableBuilder() {
    const offset = bodyRef.current?.selectionStart ?? bodyMarkdown.length;
    const existing = tableAtOffset(bodyMarkdown, offset);
    setEditingTable(existing ? { table: existing, mode: "edit", offset } : { table: emptyTable(), mode: "insert", offset });
  }

  function applyTable(next: markdownTable) {
    if (!editingTable) return;
    if (editingTable.mode === "edit") setBodyMarkdown(replaceTable(bodyMarkdown, editingTable.table, next));
    else insertBlock(formatTable(next), editingTable.offset);
    setEditingTable(null);
  }

  function setCustomSlugValue(value: string) {
    setAutomaticSlug(false);
    setSlug(slugify(value));
  }

  function resetSlug() {
    setSlug("");
    setAutomaticSlug(true);
  }

  /** The one place the form's fields become an article, so a preview cannot drift from a save. */
  function currentPayload(resolvedStatus: "draft" | "published"): articlePayload {
    return {
      title: title.trim(),
      slug: computedSlug,
      summary: summary.trim(),
      bodyMarkdown,
      publishedAt: isoFromInput(publishedAt),
      status: resolvedStatus,
      aiAssisted,
      seo: {
        metaTitle: optionalText(metaTitle),
        metaDescription: optionalText(metaDescription),
        canonicalUrl: optionalText(canonicalUrl),
        keywords: keywords.split(",").map((keyword) => keyword.trim()).filter(Boolean),
        ogImageUrl: optionalText(ogImageUrl),
        noIndex,
      },
      heroImage: heroImageUrl.trim() ? { url: heroImageUrl.trim(), alt: heroImageAlt.trim() } : null,
    };
  }

  /**
   * Preview what is in the form right now, saved or not.
   *
   * An already-open preview tab picks the new draft up from its own storage
   * listener, so it is focused rather than reloaded — reloading would throw away
   * the width the user had chosen.
   */
  function openPreview() {
    if (!savePreviewDraft(currentPayload(status), status)) {
      setFormError("The preview needs browser storage, which this window has blocked.");
      return;
    }
    setFormError("");
    if (previewWindow.current && !previewWindow.current.closed) {
      previewWindow.current.focus();
      return;
    }
    previewWindow.current = window.open(previewPath, "jackhalesPreview");
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
      await onSubmit(currentPayload(resolvedStatus));
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

        <label className="editor-field editor-checkbox editor-field-wide">
          <input type="checkbox" checked={aiAssisted} onChange={(event) => setAiAssisted(event.target.checked)} />
          <span>Show the AI-assisted badge. Set automatically whenever the article is edited with an API key.</span>
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
            <span className="editor-label-row"><span>Hero image URL</span><small>Or pick one from the library below</small></span>
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
          <button type="button" title="Insert an image" onClick={browseForImages}><ImageIcon size={17} /></button>
          <button type="button" title="Insert or edit a table" onClick={openTableBuilder}><Table size={17} /></button>
          <button type="button" title="HTML embed" onClick={() => insertToken("\n<div>\n", "\n</div>\n")}><Code2 size={17} /></button>
        </div>
      </div>

      {editingTable ? (
        <TableBuilder
          table={editingTable.table}
          mode={editingTable.mode}
          onApply={applyTable}
          onCancel={() => setEditingTable(null)}
        />
      ) : null}

      <div className="editor-content-grid">
        <label className="editor-panel">
          <span className="editor-label-row">
            <span>Markdown</span>
            <small>{library.uploading ? "Uploading image…" : "Paste or drop an image straight in"}</small>
          </span>
          <textarea
            ref={bodyRef}
            id="bodyMarkdown"
            value={bodyMarkdown}
            placeholder="Start writing in Markdown…"
            onChange={(event) => setBodyMarkdown(event.target.value)}
            onPaste={(event) => {
              const files = imageFilesFrom(event.clipboardData);
              if (!files.length) return;
              event.preventDefault();
              uploadAndInsert(files);
            }}
            onDragOver={(event) => imageFilesFrom(event.dataTransfer).length && event.preventDefault()}
            onDrop={(event) => {
              const files = imageFilesFrom(event.dataTransfer);
              if (!files.length) return;
              event.preventDefault();
              uploadAndInsert(files);
            }}
          />
        </label>
        <div className="editor-panel">
          <span>Live preview</span>
          <div className="article-editor-preview">
            {bodyMarkdown ? <MarkdownContent markdown={bodyMarkdown} /> : <div className="editor-preview-empty"><FilePreviewIcon /><p>Your formatted article will appear here.</p></div>}
          </div>
        </div>
      </div>

      <input
        ref={fileInput}
        type="file"
        accept="image/*"
        multiple
        hidden
        onChange={(event) => {
          const files = Array.from(event.target.files || []).filter((file) => file.type.startsWith("image/"));
          event.target.value = "";
          if (files.length) uploadAndInsert(files);
        }}
      />

      <ArticleImageLibrary library={library} onInsert={(markdown) => insertBlock(markdown)} onUseAsHero={useAsHero} />

      {formError ? <div className="admin-error editor-error">{formError}</div> : null}

      <div className="editor-actions">
        <button type="button" className="button button-outline" disabled={saving} onClick={onCancel}>Cancel</button>
        <div>
          <button type="button" className="button button-outline" onClick={openPreview}><Eye size={16} /> Preview</button>
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
