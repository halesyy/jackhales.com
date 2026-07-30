import { imageDimensionsFrom } from "../lib/images";

type articleFigureProps = {
  src?: string;
  alt?: string;
  /** The Markdown image title — `![alt](url "caption")` — rendered as the caption. */
  title?: string;
};

/**
 * An article image as a figure.
 *
 * Uploaded images carry their dimensions in the URL, which lets the browser
 * reserve the right amount of space before the bytes arrive instead of shoving
 * the paragraph below it down the page. Images from anywhere else simply render
 * without that hint.
 */
export function ArticleFigure({ src, alt, title }: articleFigureProps) {
  if (!src) return null;
  const size = imageDimensionsFrom(src);
  const caption = title?.trim();

  return (
    <figure className="article-figure">
      {/* Article images come from the article record and can be any external host. */}
      <img
        src={src}
        alt={alt || ""}
        width={size?.width}
        height={size?.height}
        style={size ? { aspectRatio: `${size.width} / ${size.height}` } : undefined}
        loading="lazy"
        decoding="async"
      />
      {caption ? <figcaption>{caption}</figcaption> : null}
    </figure>
  );
}
