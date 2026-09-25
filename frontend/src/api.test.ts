import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, get, post, resetForTests } from "./api";

function reply(status: number, body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

afterEach(() => {
  vi.unstubAllGlobals();
  resetForTests();
});

describe("api", () => {
  it("returns data and raises the API message on errors", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockReturnValueOnce(reply(200, { data: { a: 1 }, message: "ok" }))
      .mockReturnValueOnce(reply(404, { data: null, message: "Run not found" })));
    expect(await get("/api/v1/x")).toEqual({ a: 1 });
    await expect(get("/api/v1/y")).rejects.toEqual(new ApiError("Run not found", 404));
  });

  it("sends the CSRF token on writes and refreshes it once after a 403", async () => {
    const fetchMock = vi.fn()
      .mockReturnValueOnce(reply(200, { data: { csrf: "old" }, message: "ok" }))
      .mockReturnValueOnce(reply(403, { data: null, message: "expired" }))
      .mockReturnValueOnce(reply(200, { data: { csrf: "new" }, message: "ok" }))
      .mockReturnValueOnce(reply(201, { data: { run_id: "r1" }, message: "ok" }));
    vi.stubGlobal("fetch", fetchMock);
    expect(await post("/api/v1/projects/t/runs")).toEqual({ run_id: "r1" });
    const sent = fetchMock.mock.calls.map(([, init]) => init.headers["X-CSRF-Token"]);
    expect(sent).toEqual([undefined, "old", undefined, "new"]);
  });
});
