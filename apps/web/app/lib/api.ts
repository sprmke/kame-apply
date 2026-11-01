/** Unwraps a generated SDK result. Calls run with throwOnError, so a missing body is a bug. */
export async function ok<T>(call: Promise<{ data?: T }>): Promise<T> {
  const { data } = await call;
  if (data === undefined) throw new Error("empty response");
  return data;
}
