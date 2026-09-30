import type { CheckResult, FirmStatus, ScreenStage } from "./types";

// How a screening check and a firm's status are shown, on the grid and a firm's page.
// An eligibility criterion is met or not; a required document submitted or not.
export const MARK: Record<CheckResult, { sign: string; cls: string }> = {
  MET: { sign: "✓", cls: "met" },
  NOT_MET: { sign: "✗", cls: "not-met" },
  UNSURE: { sign: "?", cls: "unsure" },
};

const WORDS: Record<ScreenStage, Record<CheckResult, string>> = {
  ELIGIBILITY: { MET: "met", NOT_MET: "not met", UNSURE: "AI unsure" },
  DOCUMENT: { MET: "submitted", NOT_MET: "not submitted", UNSURE: "AI unsure" },
};

export const word = (stage: ScreenStage, result: CheckResult) => WORDS[stage][result];

// "2 · Consulting credential", or the title alone when there is no number to show.
export const titled = (number: string | null | undefined, title: string) =>
  number ? `${number} · ${title}` : title;

export const GROUPS: { stage: ScreenStage; label: string; note: string }[] = [
  { stage: "ELIGIBILITY", label: "Eligibility", note: "pass or fail" },
  { stage: "DOCUMENT", label: "Required documents", note: "flagged if missing, not disqualifying" },
];

export const CHIP: Record<FirmStatus, string> = {
  qualified: "chip green", not_qualified: "chip red", open: "chip amber",
  checking: "chip blue", not_checked: "chip", failed: "chip red",
};
