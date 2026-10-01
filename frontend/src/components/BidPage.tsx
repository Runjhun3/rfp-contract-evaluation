import { Link } from "react-router-dom";

type Props = { submissionId: string; firm: string; pageNo: number; pageLink: (page: number) => string };

// One page of a bid as it is in the PDF, with ‹ › to the pages around it. Used beside
// the evidence of a score and beside an eligibility check, so the committee can check
// every finding against the document itself.
export default function BidPage({ submissionId, firm, pageNo, pageLink }: Props) {
  return (
    <section className="viewer" aria-label={`Bid page ${pageNo}`}>
      <div className="spread">
        <strong>Bid page {pageNo}</strong>
        <span className="row">
          {pageNo > 1 && <Link className="btn small" to={pageLink(pageNo - 1)} aria-label="Previous page">‹</Link>}
          <Link className="btn small" to={pageLink(pageNo + 1)} aria-label="Next page">›</Link>
        </span>
      </div>
      <img className="pageimg" src={`/api/v1/submissions/${submissionId}/pages/${pageNo}.png`}
        alt={`Page ${pageNo} of ${firm}'s bid`} />
    </section>
  );
}
