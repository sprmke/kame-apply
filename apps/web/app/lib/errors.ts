/** API errors arrive as the standard envelope { error: { code, message, details } }. */
export type ApiError = { code: string; message: string; details?: unknown; status?: number };

export function toApiError(e: unknown): ApiError {
  const env = (e as { error?: { code?: string; message?: string; details?: unknown } } | null)
    ?.error;
  if (env && typeof env.code === "string") {
    return { code: env.code, message: env.message ?? "", details: env.details };
  }
  // FastAPI request validation or a network failure
  if (e instanceof TypeError) return { code: "network_error", message: e.message };
  return { code: "generic", message: "" };
}

export const errorCode = (e: unknown): string => toApiError(e).code;
