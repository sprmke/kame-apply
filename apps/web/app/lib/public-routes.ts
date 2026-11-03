/** Routes reachable while signed out. */
export const PUBLIC_EXACT = [
  "/login",
  "/register",
  "/verify-email",
  "/forgot-password",
  "/reset-password",
  "/auth/callback",
  "/_design",
  "/invite",
];

/** Prefixes that are public for every child route (legal pages must work for OAuth review). */
export const PUBLIC_PREFIXES = ["/legal"];

export function isPublicPath(path: string): boolean {
  const clean = path.replace(/\/+$/, "") || "/";
  if (PUBLIC_EXACT.includes(clean)) return true;
  return PUBLIC_PREFIXES.some((prefix) => clean === prefix || clean.startsWith(`${prefix}/`));
}
