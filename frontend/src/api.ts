// The only place that talks to the Python API. Every reply is {data, message}.
// Writes send the session's CSRF token in X-CSRF-Token; on a 403 the token is
// fetched again once (the server makes a new session key when it restarts).

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

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
  if (!res.ok) throw new ApiError(reply.message || "Something went wrong.", res.status);
  return reply.data as T;
}

async function token(refresh = false): Promise<string> {
  if (!csrf || refresh) csrf = (await call<{ csrf: string }>("GET", "/api/v1/session")).csrf;
  return csrf;
}

export function get<T>(path: string): Promise<T> {
  return call<T>("GET", path);
}

export async function post<T = null>(path: string, body?: unknown): Promise<T> {
  try {
    return await call<T>("POST", path, body);
  } catch (err) {
    if (!(err instanceof ApiError) || err.status !== 403) throw err;
    await token(true);
    return call<T>("POST", path, body);
  }
}

export function resetForTests(): void {
  csrf = null;
}
