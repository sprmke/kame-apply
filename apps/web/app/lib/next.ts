/** Only same-origin paths are valid post-login targets (blocks open redirects). */
export function safeNext(raw: unknown, fallback = "/"): string {
  if (typeof raw !== "string" || !raw.startsWith("/") || raw.startsWith("//") || raw.includes("\\"))
    return fallback;
  return raw;
}
