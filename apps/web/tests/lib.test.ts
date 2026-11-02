import { describe, expect, it } from "vitest";
import { toApiError } from "../app/lib/errors";
import { isFresh, jwtExpiry } from "../app/lib/jwt";
import { safeNext } from "../app/lib/next";

function token(payload: Record<string, unknown>): string {
  const b64 = (o: unknown) => Buffer.from(JSON.stringify(o)).toString("base64url");
  return `${b64({ alg: "none" })}.${b64(payload)}.sig`;
}

describe("jwt freshness", () => {
  it("reads exp and treats a token inside the skew window as stale", () => {
    const now = 1_700_000_000_000;
    const good = token({ exp: Math.floor(now / 1000) + 600 });
    expect(jwtExpiry(good)).toBe(Math.floor(now / 1000) + 600);
    expect(isFresh(good, 30, now)).toBe(true);
    const stale = token({ exp: Math.floor(now / 1000) + 5 });
    expect(isFresh(stale, 30, now)).toBe(false);
  });

  it("fails closed on garbage", () => {
    expect(jwtExpiry("not-a-token")).toBeNull();
    expect(jwtExpiry(token({}))).toBeNull();
    expect(isFresh(null)).toBe(false);
  });
});

describe("post-login redirects", () => {
  it("allows only same-origin paths", () => {
    expect(safeNext("/jobs?x=1")).toBe("/jobs?x=1");
    expect(safeNext("//evil.example")).toBe("/");
    expect(safeNext("https://evil.example")).toBe("/");
    expect(safeNext("/\\evil")).toBe("/");
    expect(safeNext(null, "/today")).toBe("/today");
  });
});

describe("api error envelope", () => {
  it("keeps the server code and message", () => {
    expect(toApiError({ error: { code: "budget_reached", message: "No budget" } })).toEqual({
      code: "budget_reached",
      message: "No budget",
      details: undefined,
    });
  });

  it("maps a network failure and unknown shapes", () => {
    expect(toApiError(new TypeError("Failed to fetch")).code).toBe("network_error");
    expect(toApiError("nope").code).toBe("generic");
  });
});
