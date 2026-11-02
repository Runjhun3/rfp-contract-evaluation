import { describe, expect, it } from "vitest";
import { pageList } from "./components/Pager";

describe("page numbers", () => {
  it("shows the first, the last and two either side of the current page, with gaps", () => {
    expect(pageList(6, 20)).toEqual([1, null, 4, 5, 6, 7, 8, null, 20]);
    expect(pageList(1, 20)).toEqual([1, 2, 3, null, 20]);
    expect(pageList(20, 20)).toEqual([1, null, 18, 19, 20]);
  });

  it("shows every page when there are few, and no gap of one page", () => {
    expect(pageList(2, 5)).toEqual([1, 2, 3, 4, 5]);
    expect(pageList(4, 7)).toEqual([1, 2, 3, 4, 5, 6, 7]);
    expect(pageList(1, 1)).toEqual([1]);
    expect(pageList(5, 10)).toEqual([1, 2, 3, 4, 5, 6, 7, null, 10]);
  });
});
