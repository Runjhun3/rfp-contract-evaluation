import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import type { ParticipantsPage } from "../types";

type Props = {
  data: ParticipantsPage; search: string; busy: boolean;
  onSave: (bidderIds: string[]) => void;
  onAdd: (firm: { legal_name: string; short_name: string }) => void;
};

// "Who submitted bids?": search firms, tick the participants, add a new firm.
export default function FirmPicker({ data, search, busy, onSave, onAdd }: Props) {
  const navigate = useNavigate();
  const [query, setQuery] = useState(search);
  // Participants hidden by the search stay chosen, so saving never drops them.
  const [chosen, setChosen] = useState<Set<string>>(new Set());
  const [firm, setFirm] = useState({ legal_name: "", short_name: "" });

  useEffect(() => {
    setChosen(new Set(data.submissions.map((s) => s.bidder_id)));
  }, [data]);

  const toggle = (id: string) => {
    const next = new Set(chosen);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setChosen(next);
  };
  const find = (e: FormEvent) => {
    e.preventDefault();
    navigate(query ? `?q=${encodeURIComponent(query)}` : "?");
  };
  const add = (e: FormEvent) => {
    e.preventDefault();
    onAdd(firm);
    setFirm({ legal_name: "", short_name: "" });
  };

  return (
    <section className="card">
      <h2>Who submitted bids?</h2>
      <form className="row" onSubmit={find} role="search">
        <label className="sr-only" htmlFor="q">Find a firm</label>
        <input id="q" type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Find a firm" />
        <button className="btn small" type="submit">Find</button>
      </form>
      <form onSubmit={(e) => { e.preventDefault(); onSave([...chosen]); }}>
        {data.firms.length ? data.firms.map((f) => (
          <label key={f.bidder_id} className={`check${chosen.has(f.bidder_id) ? " on" : ""}`}>
            <input type="checkbox" checked={chosen.has(f.bidder_id)} onChange={() => toggle(f.bidder_id)} /> {f.legal_name}
          </label>
        )) : <p className="muted">No firms yet. Add one below.</p>}
        {data.firms.length > 0 && <button className="btn small" type="submit" disabled={busy}>Save participants</button>}
      </form>
      <form className="drop" onSubmit={add}>
        <label className="field">Firm's legal name
          <input type="text" value={firm.legal_name} placeholder="e.g. Ernst & Young LLP" required
            onChange={(e) => setFirm({ ...firm, legal_name: e.target.value })} />
        </label>
        <label className="field">Short name
          <input type="text" value={firm.short_name} placeholder="e.g. EY"
            onChange={(e) => setFirm({ ...firm, short_name: e.target.value })} />
        </label>
        <button className="btn small" type="submit" disabled={busy}>+ Add firm to this project</button>
      </form>
    </section>
  );
}
