import { describe, expect, it } from "vitest";
import { marks, plural, reasons, titleCase } from "./format";

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

  it("pluralises and lists review reasons", () => {
    expect(plural(1, "participant")).toBe("1 participant");
    expect(plural(3, "participant")).toBe("3 participants");
    expect(reasons(["QUOTE_NOT_FOUND", "LOW_CONFIDENCE"])).toBe("quote not found, low confidence");
    expect(reasons(null)).toBe("");
  });
});
