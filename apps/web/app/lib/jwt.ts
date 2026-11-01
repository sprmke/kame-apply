/** Reads `exp` (seconds) from a JWT without verifying it; the server is the authority. */
export function jwtExpiry(token: string): number | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    const exp = (JSON.parse(json) as { exp?: number }).exp;
    return typeof exp === "number" ? exp : null;
  } catch {
    return null;
  }
}

export function isFresh(token: string | null, skewSeconds = 30, now = Date.now()): boolean {
  if (!token) return false;
  const exp = jwtExpiry(token);
  return exp !== null && exp * 1000 - now > skewSeconds * 1000;
}
