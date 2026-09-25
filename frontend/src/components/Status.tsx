import { Link } from "react-router-dom";

// What a screen shows before its data arrives, or when loading it failed.
export function Loading({ error }: { error: string | null }) {
  return (
    <main className="page">
      {error ? (
        <>
          <p className="error" role="alert">{error}</p>
          <p><Link to="/projects">Back to projects</Link></p>
        </>
      ) : (
        <p className="muted" role="status">Loading…</p>
      )}
    </main>
  );
}

export function ErrorText({ error }: { error: string | null }) {
  return error ? <p className="error" role="alert">{error}</p> : null;
}
