import { useEffect } from "react";
import { Link, Outlet } from "react-router-dom";

export function usePageTitle(title: string | null | undefined): void {
  useEffect(() => {
    document.title = title ? `${title} · Bid Evaluation` : "Bid Evaluation";
  }, [title]);
}

export default function Layout() {
  return (
    <>
      <header className="topbar">
        <Link className="brand" to="/projects">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
            <path d="M4 4h12l4 4v12H4z" />
            <path d="M8 12l3 3 5-6" />
          </svg>
          <strong>Bid Evaluation</strong>
        </Link>
      </header>
      <Outlet />
      <footer className="site">
        Marks shown here are recommendations. The Tender Evaluation Committee reviews every flagged
        item and signs the final sheet.
      </footer>
    </>
  );
}
