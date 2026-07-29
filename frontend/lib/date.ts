export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-AU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(value));
}

export function inputDate(value: string): string {
  return value.slice(0, 10);
}

/** Sibling to formatDate for values the backend sends as Unix seconds (a float) rather than an ISO string. */
export function formatUnixDate(valueSeconds: number): string {
  return new Intl.DateTimeFormat("en-AU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(valueSeconds * 1000));
}

