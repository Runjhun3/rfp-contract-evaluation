import { useEffect, useState } from "react";
import { Link, Outlet, useNavigate, useOutletContext } from "react-router-dom";
import { signOut } from "../api";
import Logo from "./Logo";
import Notice from "./Notice";
import type { Account } from "./RequireAuth";

export const PRODUCT = "BidLens";

export function usePageTitle(title: string | null | undefined): void {
  useEffect(() => {
    document.title = title ? `${title} · ${PRODUCT}` : PRODUCT;
  }, [title]);
}

export default function Layout() {
  const { user, role } = useOutletContext<Account>();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);

  async function leave() {
    setBusy(true);
    try {
      await signOut();
    } finally {
      navigate("/login", { replace: true });
    }
  }

  return (
    <>
      <header className="topbar">
        <Link className="brand" to="/projects">
          <Logo />
          <strong>{PRODUCT}</strong>
        </Link>
        <div className="row small">
          {role === "ADMIN" && <Link className="topbar-link" to="/activity">Activity</Link>}
          {role === "ADMIN" && <Link className="topbar-link" to="/users">Users</Link>}
          <span className="who">{user}</span>
          <button type="button" className="btn ghost small" onClick={leave} disabled={busy}>Sign out</button>
        </div>
      </header>
      <Notice />
      <Outlet context={{ user, role }} />
      <footer className="site">
        Marks shown here are recommendations. The Tender Evaluation Committee reviews every flagged
        item and signs the final sheet.
      </footer>
    </>
  );
}
