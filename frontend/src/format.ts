// Display helpers. Marks arrive as exact strings from the API; nothing here does maths.

export function marks(value: string | null | undefined): string {
  return value === null || value === undefined || value === "" ? "—" : value;
}

// "RFP_UPLOADED" -> "Rfp Uploaded", as the server-rendered pages showed it.
export function titleCase(value: string): string {
  return value
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

export function reasons(list: string[] | null): string {
  return (list ?? []).join(", ").replace(/_/g, " ").toLowerCase();
}
