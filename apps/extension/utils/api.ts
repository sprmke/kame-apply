import { getSession, type ExtSession } from "./storage";

export class ExtApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function headers(session: ExtSession): Promise<HeadersInit> {
  return {
    Authorization: `Bearer ${session.token}`,
    "X-Workspace-Id": session.workspaceId,
    "Content-Type": "application/json",
    Accept: "application/json",
  };
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  session?: ExtSession | null,
): Promise<T> {
  const sess = session ?? (await getSession());
  if (!sess) throw new ExtApiError("Reconnect the extension", 401);
  const url = `${sess.apiBase.replace(/\/$/, "")}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: { ...(await headers(sess)), ...(init.headers || {}) },
  });
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg =
      (body as { error?: { message?: string } })?.error?.message ||
      (body as { detail?: string })?.detail ||
      `Request failed (${res.status})`;
    throw new ExtApiError(String(msg), res.status);
  }
  return body as T;
}
