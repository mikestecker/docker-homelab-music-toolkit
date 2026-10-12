// Thin fetch wrapper. Relative paths only, so sub-path reverse proxies work.
// Auth is a session cookie (set by POST /api/auth/login) sent automatically
// by fetch's default same-origin credentials - no Authorization header is
// set here. Basic Auth still works as a fallback for curl/scripts, but the
// browser UI goes through the login page in App.tsx, not a native prompt.

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, message: string, detail: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

// Registered once by App.tsx so a session expiring mid-use (any page, any
// call) bounces back to the login screen instead of just leaving a raw error
// banner on whatever page happened to be open.
let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: (() => void) | null) {
  onUnauthorized = fn;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    if (res.status === 401 && onUnauthorized) onUnauthorized();
    const message =
      (data && typeof data === "object" && "detail" in data && String((data as { detail: unknown }).detail)) ||
      `${method} ${path} failed (${res.status})`;
    throw new ApiError(res.status, message, data);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body ?? {}),
};
