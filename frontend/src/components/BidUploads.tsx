import { Fragment, type FormEvent } from "react";
import { plural } from "../format";
import type { Submission } from "../types";

type Props = { submissions: Submission[]; busy: boolean; onUpload: (submissionId: string, form: FormData) => void };

// One row per participant: its bid file (if any) and an upload / replace form.
export default function BidUploads({ submissions, busy, onUpload }: Props) {
  const upload = (id: string) => (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    onUpload(id, new FormData(e.currentTarget));
    e.currentTarget.reset();
  };

  return (
    <section className="card">
      <h2>{plural(submissions.length, "participant")} · upload each bid</h2>
      {submissions.length ? submissions.map((s, i) => (
        <Fragment key={s.submission_id}>
          <div className="bid">
            <strong>{s.short_name}</strong>
            <span>
              {s.file_id ? (
                <>{s.file_name}<br /><span className="small muted">{s.page_count} pages · uploaded {s.uploaded}</span></>
              ) : <span className="muted">No bid uploaded yet</span>}
            </span>
            {s.file_id ? <span className="chip blue">✓ Ready</span> : <span className="chip">Waiting for file</span>}
          </div>
          <form className="row" onSubmit={upload(s.submission_id)}>
            <label className="sr-only" htmlFor={`f${i}`}>Bid PDF for {s.short_name}</label>
            <input id={`f${i}`} type="file" name="file" accept="application/pdf" required />
            <button className="btn small" type="submit" disabled={busy}>{s.file_id ? "Replace" : "Upload bid"}</button>
          </form>
        </Fragment>
      )) : <p className="muted">Tick the firms that submitted bids.</p>}
    </section>
  );
}
