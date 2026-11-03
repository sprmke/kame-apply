import { getSession, type ExtSession } from "./storage";

// The extension only ever talks to our own API. A page that hands us any other origin would
// receive the extension token and every clipped page, so the base is allowlisted.
const ALLOWED_API_ORIGINS = [
  /^http:\/\/localhost:\d+$/,
  /^http:\/\/127\.0\.0\.1:\d+$/,
  /^https:\/\/[a-z0-9-]+(\.[a-z0-9-]+)*\.kame\.apply$/,
];

export function isAllowedApiBase(base: string): boolean {
  try {
    const url = new URL(base);
    if (url.protocol !== "http:" && url.protocol !== "https:") return false;
    return ALLOWED_API_ORIGINS.some((re) => re.test(url.origin));
  } catch {
    return false;
  }
}

export function looksLikeExtensionToken(token: string): boolean {
  return typeof token === "string" && token.startsWith("ka_ext_");
}

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
