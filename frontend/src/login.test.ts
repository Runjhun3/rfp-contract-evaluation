import { describe, expect, it } from "vitest";
import { safeNext } from "./pages/Login";

describe("sign-in redirect", () => {
  it("returns only to pages of this site", () => {
    expect(safeNext("/projects/42/criteria")).toBe("/projects/42/criteria");
    expect(safeNext(null)).toBe("/projects");
    expect(safeNext("//evil.example")).toBe("/projects");
    expect(safeNext("https://evil.example")).toBe("/projects");
    expect(safeNext("/login?next=/x")).toBe("/projects");
  });
});
