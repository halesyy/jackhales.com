/**
 * Getting a picture from a clipboard into an article.
 *
 * A pasted screenshot is typically a multi-megabyte PNG at whatever resolution
 * the display happens to be. Everything here happens before the upload: the
 * image is redrawn at a sane size and re-encoded, so the library stores a couple
 * of hundred kilobytes instead of several megabytes and readers download the
 * same. Animated GIFs are the exception — redrawing one keeps only its first
 * frame, so they are sent through untouched.
 */

export const maxImageWidth = 1800;
export const maxImageBytes = 8 * 1024 * 1024;
const encodedQuality = 0.82;
const passthroughTypes = new Set(["image/gif"]);

export type preparedImage = {
  blob: Blob;
  filename: string;
  width: number;
  height: number;
};

export function isImageFile(file: File | null | undefined): boolean {
  return Boolean(file && file.type.startsWith("image/"));
}

/** Every image on a paste, drop or file-picker event, in the order they arrived. */
export function imageFilesFrom(items: DataTransfer | null | undefined): File[] {
  if (!items) return [];
  return Array.from(items.files || []).filter(isImageFile);
}

function renamed(filename: string, extension: string): string {
  const base = (filename || "image").replace(/\.[^.]+$/, "").trim() || "image";
  return `${base}.${extension}`;
}

function loadImage(source: Blob): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const objectUrl = URL.createObjectURL(source);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(objectUrl);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error("That file could not be read as an image."));
    };
    image.src = objectUrl;
  });
}

function encodeCanvas(canvas: HTMLCanvasElement, type: string): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("The image could not be encoded."))), type, encodedQuality);
  });
}

/**
 * Redraw at no more than `maxImageWidth` and encode as WebP, falling back to
 * whichever format the browser will actually produce.
 */
export async function prepareImage(file: File): Promise<preparedImage> {
  if (passthroughTypes.has(file.type)) {
    if (file.size > maxImageBytes) throw new Error("That animated image is too large — it needs to be under 8MB.");
    const original = await loadImage(file);
    return { blob: file, filename: file.name || "image.gif", width: original.naturalWidth, height: original.naturalHeight };
  }

  const image = await loadImage(file);
  const scale = Math.min(1, maxImageWidth / Math.max(image.naturalWidth, 1));
  const width = Math.max(1, Math.round(image.naturalWidth * scale));
  const height = Math.max(1, Math.round(image.naturalHeight * scale));

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("This browser could not prepare the image for upload.");
  context.drawImage(image, 0, 0, width, height);

  let blob = await encodeCanvas(canvas, "image/webp");
  let extension = "webp";
  if (!blob.type.includes("webp")) {
    // Safari before 14 and a few embedded browsers ignore the requested type.
    blob = await encodeCanvas(canvas, "image/jpeg");
    extension = "jpg";
  }
  if (blob.size > maxImageBytes) throw new Error("That image is still too large after resizing — try a smaller one.");

  return { blob, filename: renamed(file.name, extension), width, height };
}

/** A first draft of the alt text, so a pasted image is never silently undescribed. */
export function suggestAltText(filename: string): string {
  const base = filename.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " ").replace(/\s+/g, " ").trim();
  if (!base || /^(image|screenshot|pasted|clipboard|photo|img)[\s\d.]*$/i.test(base)) return "";
  return base.charAt(0).toUpperCase() + base.slice(1);
}

/**
 * The dimensions an uploaded image carries in its URL, so a figure can reserve
 * its space without a round trip. Any other URL returns null and renders as-is.
 */
export function imageDimensionsFrom(url: string): { width: number; height: number } | null {
  const match = /[?&]w=(\d{1,5})&h=(\d{1,5})(?:&|$)/.exec(url);
  if (!match) return null;
  const width = Number(match[1]);
  const height = Number(match[2]);
  return width > 0 && height > 0 ? { width, height } : null;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Markdown escaping for the two characters that would break out of `![alt](url "title")`. */
function escapeMarkdown(value: string): string {
  return value.replace(/([[\]])/g, "\\$1").replace(/"/g, "'");
}

export function imageMarkdown(url: string, alt: string, caption = ""): string {
  const title = caption.trim() ? ` "${escapeMarkdown(caption.trim())}"` : "";
  return `![${escapeMarkdown(alt.trim())}](${url}${title})`;
}
