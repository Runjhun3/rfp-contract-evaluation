import type { ReactNode } from "react";

type Props = { title: ReactNode; aside?: ReactNode; children: ReactNode };

// A card whose heading opens and closes it (a native details element, so keyboard and
// screen readers work as they do for any disclosure). Starts open.
export default function Section({ title, aside, children }: Props) {
  return (
    <details className="card section" open>
      <summary>
        <h2>{title}</h2>
        {aside}
      </summary>
      <div className="section-body">{children}</div>
    </details>
  );
}
