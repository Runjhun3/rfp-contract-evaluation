import type { HistoryRow } from "../recordTypes";

type Props = { rows: HistoryRow[]; subject: string; label: string };

// What changed in one line: "old → new" when both are known, else whichever is.
// Long values (a criterion's RFP text) scroll inside their cell.
function Details({ row }: { row: HistoryRow }) {
  const text = row.old && row.new ? `${row.old} → ${row.new}` : row.old ?? row.new;
  if (!text) return <span className="muted">—</span>;
  return <div className={`audit-text${text.length > 240 ? " long" : ""}`}>{text}</div>;
}

// A simple log, newest first: when (date and time), who, what happened, what it is
// about and the details. Only reads the record.
export default function AuditTable({ rows, subject, label }: Props) {
  return (
    <table className="table audit" aria-label={label}>
      <thead>
        <tr><th>Date &amp; time</th><th>Who</th><th>What</th><th>{subject}</th><th>Details</th></tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            <td className="num nowrap">{r.stamp}</td>
            <td>{r.who ?? "—"}</td>
            <td>{r.what}</td>
            <td>{r.code ?? "—"}</td>
            <td><Details row={r} /></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
