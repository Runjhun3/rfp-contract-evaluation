"""Load prompt files by name and fill {{placeholders}}. See docs/prompts.md.

Changing a prompt = new file + bump the version here. Never edit a shipped one.
"""
import re
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"

VERSIONS = {
    "system": "system_v1",
    "item": "item_eval_v1",
    "criterion": "criterion_eval_v1",
    "label": "page_label_v1",
    "criteria": "criteria_extraction_v1",
}

_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


class PromptError(ValueError):
    pass


def load(name: str) -> str:
    if name not in VERSIONS:
        raise PromptError(f"unknown prompt {name!r}")
    return (PROMPT_DIR / f"{VERSIONS[name]}.md").read_text(encoding="utf-8")


def fill(template: str, **values: object) -> str:
    def swap(match: re.Match) -> str:
        key = match.group(1)
        if key not in values:
            raise PromptError(f"missing placeholder {{{{{key}}}}}")
        return str(values[key])

    return _PLACEHOLDER.sub(swap, template)


def versions() -> dict[str, str]:
    return dict(VERSIONS)
