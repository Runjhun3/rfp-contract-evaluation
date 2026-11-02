import { Fragment, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { post } from "../api";
import AuditTable from "../components/AuditTable";
import BackLink from "../components/BackLink";
import { usePageTitle } from "../components/Layout";
import NewUserForm from "../components/NewUserForm";
import { ErrorText, Loading } from "../components/Status";
import type { UserRow, UsersPage } from "../recordTypes";
import { useApi } from "../useApi";

// Administrators only: the named sign-in accounts, a new account, switching an account
// off or on, and setting a new password. Accounts are never deleted, because decisions
// and the audit trail name them. The .env administrator is not listed here.
export default function Users() {
  usePageTitle("Users");
  const { data, error, reload } = useApi<UsersPage>("/api/v1/users");
  const [actionError, setActionError] = useState<string | null>(null);
  const [resetFor, setResetFor] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  if (!data) return <Loading error={error} />;

  async function act(path: string, body: unknown, after?: () => void) {
    setBusy(true);
    setActionError(null);
    try {
      await post(path, body);
      after?.();
      reload();
    } catch (err) {
      setActionError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const toggle = (u: UserRow) => {
    if (u.is_active && !window.confirm(`Switch off ${u.username}? They are signed out and can no longer sign in.`)) return;
    act(`/api/v1/users/${u.user_id}/active`, { active: !u.is_active });
  };
  const savePassword = (e: FormEvent, u: UserRow) => {
    e.preventDefault();
    act(`/api/v1/users/${u.user_id}/password`, { password }, () => { setResetFor(null); setPassword(""); });
  };

  return (
    <main className="page">
      <div className="back-row">
        <BackLink to="/projects" label="projects" />
        <nav className="crumbs" aria-label="Breadcrumb"><Link to="/projects">Projects</Link> / Users</nav>
      </div>
      <div>
        <h1>Users</h1>
        <p className="sub">Accounts that can sign in to BidLens. Every action is recorded against the account that made it.</p>
      </div>
      <ErrorText error={actionError} />
      {data.users.length ? (
        <table className="table">
          <thead>
            <tr><th>Username</th><th>Name</th><th>Role</th><th>Status</th><th>Created</th><th><span className="sr-only">Actions</span></th></tr>
          </thead>
          <tbody>
            {data.users.map((u) => (
              <Fragment key={u.user_id}>
                <tr className={u.is_active ? undefined : "out"}>
                  <td><strong>{u.username}</strong></td>
                  <td>{u.full_name}</td>
                  <td>{u.role_label}</td>
                  <td><span className={`chip${u.is_active ? " blue" : ""}`}>{u.is_active ? "Active" : "Switched off"}</span></td>
                  <td className="small muted">{u.created}{u.created_by && <><br />by {u.created_by}</>}</td>
                  <td className="right nowrap">
                    <button className="btn small" type="button" disabled={busy}
                      onClick={() => { setResetFor(resetFor === u.user_id ? null : u.user_id); setPassword(""); }}>Set password</button>{" "}
                    <button className="btn small quiet" type="button" disabled={busy} onClick={() => toggle(u)}>
                      {u.is_active ? "Switch off" : "Switch on"}
                    </button>
                  </td>
                </tr>
                {resetFor === u.user_id && (
                  <tr>
                    <td colSpan={6}>
                      <form className="row" onSubmit={(e) => savePassword(e, u)}>
                        <label className="sr-only" htmlFor="reset-password">New password for {u.username}</label>
                        <input id="reset-password" type="password" autoComplete="new-password" minLength={12} required
                          placeholder={`New password for ${u.username}`} value={password} onChange={(e) => setPassword(e.target.value)} />
                        <button className="btn small primary" type="submit" disabled={busy}>Save password</button>
                        <button className="btn small" type="button" onClick={() => setResetFor(null)}>Cancel</button>
                      </form>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      ) : <div className="card"><p className="muted">No accounts yet besides the built-in administrator.</p></div>}
      <NewUserForm roles={data.roles} onSaved={reload} />
      {data.events.length > 0 && (
        <section className="page-form">
          <h2>Recent account changes</h2>
          <AuditTable rows={data.events} subject="Account" label="Recent account changes" />
        </section>
      )}
    </main>
  );
}
