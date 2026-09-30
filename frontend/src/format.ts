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

// Page numbers with each run of consecutive pages as a range: [30, 32, 33, 34] -> "30, 32–34".
export function pageRanges(pages: number[]): string {
  const runs: [number, number][] = [];
  for (const p of [...new Set(pages)].sort((a, b) => a - b)) {
    const last = runs[runs.length - 1];
    if (last && p === last[1] + 1) last[1] = p;
    else runs.push([p, p]);
  }
  return runs.map(([a, b]) => (a === b ? `${a}` : `${a}–${b}`)).join(", ");
}

// A run is over once every participant is DONE or FAILED (the API sets run.status).
export function runFinished(status: string): boolean {
  return status === "DONE" || status === "FAILED";
}
