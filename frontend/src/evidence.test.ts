import { describe, expect, it } from "vitest";
import { nextCounted } from "./pages/Evidence";
import type { ItemGroup, ItemRow } from "./types";

const row = (item_id: string, decided = false): ItemRow => ({
  item_id, title: item_id, pages: "p. 1", marks: "1", attention: false, decision: decided ? "ACCEPT" : null,
});

describe("evidence: the next counted item", () => {
  const groups: ItemGroup[] = [
    { key: "counted", label: "Counted", items: [row("a"), row("b", true), row("c"), row("d")] },
    { key: "not_counted", label: "Not counted", items: [row("x")] },
  ];

  it("skips decided items and goes on after the current one", () => {
    expect(nextCounted(groups, "a")).toBe("c");
    expect(nextCounted(groups, "c")).toBe("d");
  });

  it("wraps to the top, and starts at the top from an item that is not counted", () => {
    expect(nextCounted(groups, "d")).toBe("a");
    expect(nextCounted(groups, "x")).toBe("a");
  });

  it("is null when every other counted item is decided", () => {
    const one: ItemGroup[] = [{ key: "counted", label: "Counted", items: [row("a"), row("b", true)] }];
    expect(nextCounted(one, "a")).toBeNull();
    expect(nextCounted([], null)).toBeNull();
  });
});
