import { Link } from "react-router-dom";

type Props = { page: number; pages: number; total: number; perPage: number; link: (page: number) => string };

// The page numbers to show: the first, the last, and two either side of the current
// one; null marks a gap ("…"), and a gap of a single page shows that page instead.
// [1, null, 4, 5, 6, 7, 8, null, 20] for page 6 of 20.
export function pageList(page: number, pages: number): (number | null)[] {
  const shown = [...new Set([1, pages, ...[-2, -1, 0, 1, 2].map((d) => page + d)])]
    .filter((p) => p >= 1 && p <= pages).sort((a, b) => a - b);
  return shown.flatMap((p, i) => {
    const gap = i > 0 ? p - shown[i - 1] : 1;
    return gap === 2 ? [p - 1, p] : gap > 2 ? [null, p] : [p];
  });
}

// Numbered pages for a long list, with Previous / Next and which rows are shown.
export default function Pager({ page, pages, total, perPage, link }: Props) {
  const first = total ? (page - 1) * perPage + 1 : 0;
  const last = Math.min(page * perPage, total);
  return (
    <div className="spread pager">
      <span className="small muted">Showing {first}–{last} of {total}</span>
      {pages > 1 && (
        <nav className="row pages" aria-label="Pages">
          {page > 1 ? <Link className="btn small" to={link(page - 1)}>‹ Previous</Link>
            : <span className="btn small" aria-disabled="true">‹ Previous</span>}
          {pageList(page, pages).map((p, i) => p === null ? <span key={`gap${i}`} className="muted">…</span>
            : p === page ? <span key={p} className="btn small current" aria-current="page">{p}</span>
              : <Link key={p} className="btn small" to={link(p)} aria-label={`Page ${p}`}>{p}</Link>)}
          {page < pages ? <Link className="btn small" to={link(page + 1)}>Next ›</Link>
            : <span className="btn small" aria-disabled="true">Next ›</span>}
        </nav>
      )}
    </div>
  );
}
