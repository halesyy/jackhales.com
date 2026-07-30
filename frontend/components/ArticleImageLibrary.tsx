import { Check, Copy, ImageIcon, Star, Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";

import { formatBytes, imageMarkdown } from "../lib/images";
import type { imageAsset } from "../lib/types";
import type { imageLibrary } from "../lib/useImageLibrary";

type articleImageLibraryProps = {
  library: imageLibrary;
  onInsert: (markdown: string) => void;
  onUseAsHero: (image: imageAsset) => void;
};

/**
 * The image block.
 *
 * Every image the site has ever stored, each with the one thing Markdown cannot
 * hold on its own — its alt text — kept next to the picture it describes. Alt
 * text saves against the image itself, so the next article that uses it starts
 * out described rather than blank.
 */
export function ArticleImageLibrary({ library, onInsert, onUseAsHero }: articleImageLibraryProps) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [copiedId, setCopiedId] = useState("");
  const [dragging, setDragging] = useState(false);

  function altValue(image: imageAsset): string {
    return drafts[image.id] ?? image.alt;
  }

  function commitAlt(image: imageAsset) {
    const next = (drafts[image.id] ?? "").trim();
    if (drafts[image.id] === undefined || next === image.alt) return;
    library.setAlt(image.id, next);
  }

  async function copyUrl(image: imageAsset) {
    try {
      await navigator.clipboard.writeText(image.url);
      setCopiedId(image.id);
      window.setTimeout(() => setCopiedId((current) => (current === image.id ? "" : current)), 1600);
    } catch {
      // Copying can be blocked; the URL is still visible in the inserted Markdown.
    }
  }

  function confirmRemove(image: imageAsset) {
    if (!window.confirm(`Remove ${image.filename || "this image"} from the library? Articles already using it will keep working only if none do.`)) return;
    library.remove(image.id);
  }

  function chooseFiles(files: FileList | null) {
    const chosen = Array.from(files || []).filter((file) => file.type.startsWith("image/"));
    if (chosen.length) library.uploadFiles(chosen);
    if (fileInput.current) fileInput.current.value = "";
  }

  return (
    <section className="image-library">
      <div className="image-library-heading">
        <div>
          <p className="eyebrow">Images</p>
          <h3>Paste, drop or upload — then describe it.</h3>
        </div>
        <span>
          {library.images.length} stored · {formatBytes(library.bytesUsed)} used · {formatBytes(library.bytesAvailable)} free
        </span>
      </div>

      <div
        className={`image-dropzone${dragging ? " image-dropzone-active" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          chooseFiles(event.dataTransfer.files);
        }}
      >
        <Upload size={18} />
        <p>Drop images here, or paste one straight into the Markdown box.</p>
        <button type="button" className="button button-outline" onClick={() => fileInput.current?.click()}>
          Choose images
        </button>
        <input
          ref={fileInput}
          type="file"
          accept="image/*"
          multiple
          hidden
          onChange={(event) => chooseFiles(event.target.files)}
        />
      </div>

      {library.uploading ? (
        <p className="image-library-status">Preparing and uploading {library.uploading} image{library.uploading === 1 ? "" : "s"}…</p>
      ) : null}
      {library.error ? (
        <div className="admin-error image-library-error">
          {library.error}
          <button type="button" onClick={library.clearError}>Dismiss</button>
        </div>
      ) : null}

      {library.loading ? <p className="image-library-status">Loading the library…</p> : null}

      {library.images.length ? (
        <ul className="image-grid">
          {library.images.map((image) => (
            <li key={image.id} className="image-card">
              <div className="image-card-preview">
                {/* Stored images are served by the API on another origin. */}
                <img src={image.url} alt={image.alt} width={image.width} height={image.height} loading="lazy" />
              </div>
              <div className="image-card-body">
                <div className="image-card-meta">
                  <strong title={image.filename}>{image.filename || "Untitled image"}</strong>
                  <small>{image.width}×{image.height} · {formatBytes(image.byteSize)}</small>
                </div>
                <label className="image-card-alt">
                  <span className="editor-label-row">
                    <span>Alt text</span>
                    <small className={altValue(image).trim() ? undefined : "image-alt-missing"}>
                      {altValue(image).trim() ? `${altValue(image).trim().length}/300` : "Needed for screen readers"}
                    </small>
                  </span>
                  <input
                    value={altValue(image)}
                    maxLength={300}
                    placeholder="What the image shows"
                    onChange={(event) => setDrafts((current) => ({ ...current, [image.id]: event.target.value }))}
                    onBlur={() => commitAlt(image)}
                    onKeyDown={(event) => event.key === "Enter" && event.currentTarget.blur()}
                  />
                </label>
                <div className="image-card-actions">
                  <button
                    type="button"
                    className="button button-dark"
                    onClick={() => onInsert(imageMarkdown(image.url, altValue(image)))}
                  >
                    <ImageIcon size={14} /> Insert
                  </button>
                  <button type="button" className="button button-outline" title="Use as the hero image" onClick={() => onUseAsHero(image)}>
                    <Star size={14} /> Hero
                  </button>
                  <button type="button" className="button button-outline" title="Copy the image URL" onClick={() => copyUrl(image)}>
                    {copiedId === image.id ? <Check size={14} /> : <Copy size={14} />}
                  </button>
                  <button type="button" className="button button-outline image-card-remove" title="Remove from the library" onClick={() => confirmRemove(image)}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        !library.loading && <p className="image-library-status">No images yet. Paste one into the article and it lands here.</p>
      )}
    </section>
  );
}
