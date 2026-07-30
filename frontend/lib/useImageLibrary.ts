import { useCallback, useEffect, useState } from "react";

import { deleteImage, fetchImageLibrary, updateImageAlt, uploadImage } from "./api";
import { prepareImage, suggestAltText } from "./images";
import type { imageAsset } from "./types";

export type imageLibrary = {
  images: imageAsset[];
  bytesUsed: number;
  bytesAvailable: number;
  loading: boolean;
  uploading: number;
  error: string;
  clearError: () => void;
  /** Resizes, uploads and adds each file to the library, returning what was stored. */
  uploadFiles: (files: File[]) => Promise<imageAsset[]>;
  setAlt: (imageId: string, alt: string) => Promise<void>;
  remove: (imageId: string) => Promise<void>;
};

function describe(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

/**
 * The editor's view of the image library.
 *
 * One copy of this state serves both the paste handler and the library panel, so
 * an image pasted into the body shows up in the panel without a reload.
 */
export function useImageLibrary(enabled: boolean): imageLibrary {
  const [images, setImages] = useState<imageAsset[]>([]);
  const [bytesUsed, setBytesUsed] = useState(0);
  const [bytesAvailable, setBytesAvailable] = useState(0);
  const [loading, setLoading] = useState(enabled);
  const [uploading, setUploading] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!enabled) return;
    let active = true;

    fetchImageLibrary()
      .then((library) => {
        if (!active) return;
        setImages(library.images);
        setBytesUsed(library.bytesUsed);
        setBytesAvailable(library.bytesAvailable);
      })
      .catch((cause) => active && setError(describe(cause, "The image library could not be loaded.")))
      .finally(() => active && setLoading(false));

    return () => {
      active = false;
    };
  }, [enabled]);

  const absorb = useCallback((image: imageAsset) => {
    setImages((current) => {
      // An image already in the library was stored once; uploading it again is a no-op.
      const existing = current.some((item) => item.id === image.id);
      if (!existing) setBytesUsed((used) => used + image.byteSize);
      if (!existing) setBytesAvailable((available) => Math.max(available - image.byteSize, 0));
      return existing ? current.map((item) => (item.id === image.id ? image : item)) : [image, ...current];
    });
  }, []);

  const uploadFiles = useCallback(
    async (files: File[]): Promise<imageAsset[]> => {
      if (!files.length) return [];
      setError("");
      setUploading((count) => count + files.length);

      const stored: imageAsset[] = [];
      for (const file of files) {
        try {
          const prepared = await prepareImage(file);
          const image = await uploadImage(prepared.blob, prepared.filename, suggestAltText(prepared.filename));
          absorb(image);
          stored.push(image);
        } catch (cause) {
          setError(describe(cause, `${file.name || "That image"} could not be uploaded.`));
        } finally {
          setUploading((count) => Math.max(count - 1, 0));
        }
      }
      return stored;
    },
    [absorb],
  );

  const setAlt = useCallback(async (imageId: string, alt: string) => {
    try {
      const updated = await updateImageAlt(imageId, alt);
      setImages((current) => current.map((image) => (image.id === imageId ? updated : image)));
    } catch (cause) {
      setError(describe(cause, "The alt text could not be saved."));
    }
  }, []);

  const remove = useCallback(async (imageId: string) => {
    try {
      await deleteImage(imageId);
      setImages((current) => {
        const removed = current.find((image) => image.id === imageId);
        if (removed) {
          setBytesUsed((used) => Math.max(used - removed.byteSize, 0));
          setBytesAvailable((available) => available + removed.byteSize);
        }
        return current.filter((image) => image.id !== imageId);
      });
    } catch (cause) {
      setError(describe(cause, "That image could not be removed."));
    }
  }, []);

  return {
    images,
    bytesUsed,
    bytesAvailable,
    loading,
    uploading,
    error,
    clearError: useCallback(() => setError(""), []),
    uploadFiles,
    setAlt,
    remove,
  };
}
