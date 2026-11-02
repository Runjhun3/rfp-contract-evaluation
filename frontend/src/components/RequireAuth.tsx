import { useEffect, useState } from "react";
import { Navigate, Outlet, useLocation, useOutletContext } from "react-router-dom";
import { SIGNED_OUT, session, type Session } from "../api";

// Who is signed in, for the top bar (Layout reads it with useOutletContext).
export interface Account { user: string; role: string | null }

// The signed-in account, anywhere inside the app's layout (Layout passes it on).
export function useAccount(): Account {
  return useOutletContext<Account>();
}

// Shows the app only to a signed-in session; anyone else goes to /login and comes
// back to the page they asked for. The server enforces the same rule on every API call.
export default function RequireAuth() {
  const [account, setAccount] = useState<Account | null | undefined>(undefined);
  const location = useLocation();

  useEffect(() => {
    let alive = true;
    const signedIn = (s: Session) => (s.user ? { user: s.user, role: s.role } : null);
    session().then((s) => alive && setAccount(signedIn(s))).catch(() => alive && setAccount(null));
    const out = () => setAccount(null);
    window.addEventListener(SIGNED_OUT, out);
    return () => {
      alive = false;
      window.removeEventListener(SIGNED_OUT, out);
    };
  }, []);

  if (account === undefined) return <p className="muted page" role="status">Loading…</p>;
  if (account === null) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  return <Outlet context={account} />;
}
