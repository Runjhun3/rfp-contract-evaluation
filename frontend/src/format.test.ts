import { describe, expect, it } from "vitest";
import { marks, plural, runFinished, titleCase } from "./format";

describe("format", () => {
  it("shows marks exactly as the API sent them, or a dash", () => {
    expect(marks("12")).toBe("12");
    expect(marks("9.5")).toBe("9.5");
    expect(marks(null)).toBe("—");
    expect(marks("")).toBe("—");
  });

  it("title-cases status codes", () => {
    expect(titleCase("RFP_UPLOADED")).toBe("Rfp Uploaded");
    expect(titleCase("REVIEW")).toBe("Review");
  });

  it("pluralises", () => {
    expect(plural(1, "participant")).toBe("1 participant");
    expect(plural(3, "participant")).toBe("3 participants");
  });

  it("treats a run as finished once it is DONE or FAILED", () => {
    expect(runFinished("DONE")).toBe(true);
    expect(runFinished("FAILED")).toBe(true);
    expect(runFinished("RUNNING")).toBe(false);
  });
});
