import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { session, signIn } from "../api";
import LoginArt from "../components/LoginArt";
import Logo from "../components/Logo";
import { PRODUCT, usePageTitle } from "../components/Layout";

// Only same-site paths: "/projects/1" is fine, "//evil.example" or "https://…" is not.
export function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") && !next.startsWith("/login") ? next : "/projects";
}

export default function Login() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const next = safeNext(params.get("next"));
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  usePageTitle("Sign in");

  useEffect(() => {
    session().then((s) => s.user && navigate(next, { replace: true })).catch(() => undefined);
  }, [navigate, next]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(username, password);
      navigate(next, { replace: true });
    } catch (err) {
      setError((err as Error).message);
      setPassword("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <main className="login-side">
        <div className="login-brand"><span className="login-mark"><Logo size={24} /></span><strong>{PRODUCT}</strong></div>
        <form className="login-form" onSubmit={submit} noValidate>
          <div>
            <h1>Sign in</h1>
            <p className="sub">Use the account your administrator gave you.</p>
          </div>
          {error && <p className="error" role="alert">{error}</p>}
          <label className="field" htmlFor="username">Username
            <input id="username" type="text" autoComplete="username" autoCapitalize="none" spellCheck={false}
              value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus />
          </label>
          <label className="field" htmlFor="password">Password
            <span className="password">
              <input id="password" type={show ? "text" : "password"} autoComplete="current-password"
                value={password} onChange={(e) => setPassword(e.target.value)} required />
              <button type="button" className="reveal" onClick={() => setShow((s) => !s)}
                aria-pressed={show} aria-controls="password">{show ? "Hide" : "Show"}</button>
            </span>
          </label>
          <button className="btn primary wide" type="submit" disabled={busy || !username || !password}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="login-note small muted">
          Authorised users only. Bids and CVs in {PRODUCT} are confidential.
        </p>
      </main>
      <LoginArt />
    </div>
  );
}
