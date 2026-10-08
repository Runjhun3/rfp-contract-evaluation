import { Link, useSearchParams } from "react-router-dom";
import type { Region } from "../types";

type Props = { submissionId: string; firm: string; pageNo: number; pageLink: (page: number) => string };

// A region as the page link carries it (&box=x,y,w,h), and back.
export const boxParam = (r: Region) => `&box=${[r.x, r.y, r.w, r.h].map((v) => v.toFixed(4)).join(",")}`;
function readBox(value: string | null): Region | null {
  const [x, y, w, h] = (value ?? "").split(",").map(Number);
  return [x, y, w, h].every((v) => Number.isFinite(v)) && w > 0 && h > 0 ? { x, y, w, h } : null;
}

// One page of a bid as it is in the PDF, with ‹ › to the pages around it. Used beside
// the evidence of a score and beside an eligibility check, so the committee can check
// every finding against the document itself. A document check's finding opened from its
// row is outlined on the page.
export default function BidPage({ submissionId, firm, pageNo, pageLink }: Props) {
  const box = readBox(useSearchParams()[0].get("box"));
  return (
    <section className="viewer" aria-label={`Bid page ${pageNo}`}>
      <div className="spread">
        <strong>Bid page {pageNo}</strong>
        <span className="row">
          {pageNo > 1 && <Link className="btn small" to={pageLink(pageNo - 1)} aria-label="Previous page">‹</Link>}
          <Link className="btn small" to={pageLink(pageNo + 1)} aria-label="Next page">›</Link>
        </span>
      </div>
      <div className="pageframe">
        <img className="pageimg" src={`/api/v1/submissions/${submissionId}/pages/${pageNo}.png`}
          alt={`Page ${pageNo} of ${firm}'s bid`} />
        {box && (
          <div className="pagebox" role="img" aria-label="The part of the page the check is about"
            style={{ left: `${box.x * 100}%`, top: `${box.y * 100}%`,
                     width: `${box.w * 100}%`, height: `${box.h * 100}%` }} />
        )}
      </div>
    </section>
  );
}
