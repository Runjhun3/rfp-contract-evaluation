// The only place that talks to the Python API. Every reply is {data, message}.
// Writes send the session's CSRF token in X-CSRF-Token; on a 403 the token is
// fetched again once (the server makes a new session key when it restarts).
// A 401 means the session is not signed in: SIGNED_OUT is dispatched on window
// so RequireAuth can send the user to the sign-in page.

export const SIGNED_OUT = "bidlens:signed-out";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export interface Session { csrf: string; user: string | null }

let csrf: string | null = null;

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") headers["X-CSRF-Token"] = await token();
  const isForm = body instanceof FormData;
  if (body !== undefined && !isForm) headers["Content-Type"] = "application/json";
  const ctrl = new AbortController();
  const timer = method === "GET" ? setTimeout(() => ctrl.abort(), 20000) : undefined;
  let res: Response;
  try {
    res = await fetch(path, {
      method, headers, credentials: "same-origin", signal: ctrl.signal,
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("The server did not answer. Check it is running and try again.", 0);
  } finally {
    clearTimeout(timer);
  }
  const reply = await res.json().catch(() => ({ data: null, message: res.statusText }));
  if (res.status === 401 && path !== "/api/v1/login" && typeof window !== "undefined") {
    window.dispatchEvent(new Event(SIGNED_OUT));
  }
  if (!res.ok) throw new ApiError(reply.message || "Something went wrong.", res.status);
  return reply.data as T;
}

async function token(refresh = false): Promise<string> {
  if (!csrf || refresh) csrf = (await call<Session>("GET", "/api/v1/session")).csrf;
  return csrf;
}

export function get<T>(path: string): Promise<T> {
  return call<T>("GET", path);
}

// A write; on a 403 the CSRF token is fetched again and the write retried once.
async function write<T>(method: string, path: string, body?: unknown): Promise<T> {
  try {
    return await call<T>(method, path, body);
  } catch (err) {
    if (!(err instanceof ApiError) || err.status !== 403) throw err;
    await token(true);
    return call<T>(method, path, body);
  }
}

export function post<T = null>(path: string, body?: unknown): Promise<T> {
  return write<T>("POST", path, body);
}

export function del(path: string): Promise<null> {
  return write<null>("DELETE", path);
}

// Who is signed in (null if nobody); also refreshes the CSRF token.
export async function session(): Promise<Session> {
  const s = await call<Session>("GET", "/api/v1/session");
  csrf = s.csrf;
  return s;
}

// The server starts a new session on sign-in, with a new CSRF token.
export async function signIn(username: string, password: string): Promise<string> {
  const s = await post<{ csrf: string; user: string }>("/api/v1/login", { username, password });
  csrf = s.csrf;
  return s.user;
}

export async function signOut(): Promise<void> {
  await post("/api/v1/logout");
  csrf = null;
}

export function resetForTests(): void {
  csrf = null;
}
