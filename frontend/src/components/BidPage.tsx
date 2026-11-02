import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

type Props = { submissionId: string; firm: string; pageNo: number; pageLink: (page: number) => string };

// One page of a bid as it is in the PDF, with ‹ › to the pages around it and a box to
// type a page number. Used beside the evidence of a score and beside an eligibility
// check, so the committee can check every finding against the document itself.
export default function BidPage({ submissionId, firm, pageNo, pageLink }: Props) {
  return (
    <section className="viewer" aria-label={`Bid page ${pageNo}`}>
      <div className="spread">
        <strong>Bid page {pageNo}</strong>
        <span className="row">
          {pageNo > 1 && <Link className="btn small" to={pageLink(pageNo - 1)} aria-label="Previous page">‹</Link>}
          <GoToPage key={pageNo} pageNo={pageNo} pageLink={pageLink} />
          <Link className="btn small" to={pageLink(pageNo + 1)} aria-label="Next page">›</Link>
        </span>
      </div>
      <img className="pageimg" src={`/api/v1/submissions/${submissionId}/pages/${pageNo}.png`}
        alt={`Page ${pageNo} of ${firm}'s bid`} />
    </section>
  );
}

// Enter opens the typed page; leaving the box without Enter puts the current page back.
// Keyed by the page shown, so the box always starts with the current page number.
function GoToPage({ pageNo, pageLink }: Pick<Props, "pageNo" | "pageLink">) {
  const navigate = useNavigate();
  const [value, setValue] = useState(String(pageNo));

  function go(e: FormEvent) {
    e.preventDefault();
    const page = Math.trunc(Number(value));
    if (page >= 1 && page !== pageNo) navigate(pageLink(page));
    else setValue(String(pageNo));
  }

  return (
    <form className="page-go" onSubmit={go}>
      <label className="sr-only" htmlFor="bid-page-no">Go to page</label>
      <input id="bid-page-no" className="page-no num" type="number" inputMode="numeric" min={1} step={1}
        value={value} onChange={(e) => setValue(e.target.value)} onBlur={() => setValue(String(pageNo))}
        onFocus={(e) => e.target.select()} />
    </form>
  );
}
