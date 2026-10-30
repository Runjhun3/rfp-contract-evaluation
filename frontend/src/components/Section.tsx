import type { ReactNode } from "react";

type Props = {
  title: ReactNode; aside?: ReactNode; children: ReactNode;
  open?: boolean; onToggle?: (open: boolean) => void; // set both to open or close it from outside
};

// A card whose heading opens and closes it (a native details element, so keyboard and
// screen readers work as they do for any disclosure). Starts open.
export default function Section({ title, aside, children, open = true, onToggle }: Props) {
  return (
    <details className="card section" open={open}
      onToggle={onToggle && ((e) => onToggle(e.currentTarget.open))}>
      <summary>
        <h2>{title}</h2>
        {aside}
      </summary>
      <div className="section-body">{children}</div>
    </details>
  );
}
