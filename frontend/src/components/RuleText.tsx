import type { Prompt } from "../types";
import Section from "./Section";

type Props = {
  prompt: Prompt | null;
  text: string;
  onChange: (text: string) => void;
  notice: string | null;    // what the last save or rebuild did to the rule text
  onRebuild: () => void;
  canRebuild: boolean;      // false while criteria edits are unsaved
  busy: boolean;
};

// The rule text the evaluator applies. Saving criteria updates it from them unless the
// committee wrote its own text; "Rebuild from the criteria" fills the box from the saved
// criteria for review, and nothing is saved until "Save changes".
export default function RuleText({ prompt, text, onChange, notice, onRebuild, canRebuild,
  busy }: Props) {
  const version = prompt && ` · version ${prompt.version} (${prompt.status.toLowerCase()})`;
  return (
    <Section title={<>Rule text used by the evaluator{version}</>}>
      <div className="spread">
        <p className="small muted">
          Only criteria marked "Scored per: Project/CV" and "AI + committee" are evaluated
          from the bids.
        </p>
        <button className="btn small" type="button" onClick={onRebuild}
          disabled={busy || !canRebuild}
          title={canRebuild ? "Fill the box from the saved criteria"
            : "Save your criteria changes first"}>
          Rebuild from the criteria
        </button>
      </div>
      {notice && <div className="notice info" role="status">{notice}</div>}
      <label className="sr-only" htmlFor="block">Rule text</label>
      <textarea id="block" rows={16} value={text} onChange={(e) => onChange(e.target.value)} />
    </Section>
  );
}
