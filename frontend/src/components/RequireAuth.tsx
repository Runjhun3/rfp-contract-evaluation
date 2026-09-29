import { useEffect, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { SIGNED_OUT, session } from "../api";

// Shows the app only to a signed-in session; anyone else goes to /login and comes
// back to the page they asked for. The server enforces the same rule on every API call.
export default function RequireAuth() {
  const [user, setUser] = useState<string | null | undefined>(undefined);
  const location = useLocation();

  useEffect(() => {
    let alive = true;
    session().then((s) => alive && setUser(s.user)).catch(() => alive && setUser(null));
    const out = () => setUser(null);
    window.addEventListener(SIGNED_OUT, out);
    return () => {
      alive = false;
      window.removeEventListener(SIGNED_OUT, out);
    };
  }, []);

  if (user === undefined) return <p className="muted page" role="status">Loading…</p>;
  if (user === null) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  return <Outlet context={user} />;
}
