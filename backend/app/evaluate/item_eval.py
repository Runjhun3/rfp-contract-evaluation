"""EVAL_ITEM: one LLM call per item (project section or CV), one criterion. If Python
recomputes one of the item's numeric/date tests differently, one re-check call."""
from pathlib import Path

from dateutil.relativedelta import relativedelta

from app.evaluate.condition_check import condition_checks, findings
from app.ingest.page_render import render_pngs
from app.llm.client import LlmClient
from app.llm.prompts import fill, load
from app.schemas.llm import ItemResult, Recheck
from app.schemas.records import Item, Page, RunContext

MAX_IMAGES = 20   # Bedrock accepts at most 20 images per request


def system_prompt(ctx: RunContext, criteria_block: str) -> str:
    minus_12m = _minus_12m(ctx)
    rules = fill(load("system"), department=ctx.department,
                 bid_due_date=ctx.bid_due_date.isoformat(), bid_due_minus_12m=minus_12m)
    return f"{rules}\n{fill(criteria_block, bid_due_minus_12m=minus_12m)}"


def evaluate_item(item: Item, pages: dict[int, Page], ctx: RunContext, system: str,
                  llm: LlmClient, bid_pdf: Path | None = None) -> ItemResult:
    images = item_images(bid_pdf, item) if bid_pdf else {}
    text = render_pages(item, pages)
    if images:
        shown = ", ".join(map(str, images))
        text = f"[The page images above are PDF p. {shown}, in order]\n\n{text}"
    user = fill(load("item"), bidder=ctx.bidder, label=item.label, kind=item.kind,
                code=item.criterion_code, pages=text)
    result = _ask(llm, system, user, images, item)
    wrong = findings(condition_checks(result, ctx.bid_due_date))
    if not wrong:
        return result
    return _recheck(llm, system, user, images, item, result, wrong)


def _recheck(llm: LlmClient, system: str, user: str, images: dict[int, bytes], item: Item,
             first: ItemResult, wrong: list[str]) -> ItemResult:
    """Once only: send the item back with the tests Python recomputed differently. The
    second answer stands (and is checked again later); the first is kept on record."""
    again = fill(load("recheck"), previous=first.model_dump_json(exclude={"recheck"}),
                 findings="\n".join(f"- {w}" for w in wrong))
    result = _ask(llm, system, f"{user}\n\n{again}", images, item)
    result.recheck = Recheck(first_eligible=first.eligible, first_marks=first.marks,
                             first_reason=first.reason, findings=wrong)
    return result


def _ask(llm: LlmClient, system: str, user: str, images: dict[int, bytes],
         item: Item) -> ItemResult:
    result = llm.ask_json(system, user, ItemResult, list(images.values()))
    result.label, result.code, result.recheck = item.label, item.criterion_code, None
    return result


def item_images(bid_pdf: Path, item: Item) -> dict[int, bytes]:
    """Page images for a CV: its tables often have a text layer out of reading order."""
    if item.kind != "CV":
        return {}
    return render_pngs(bid_pdf, list(range(item.from_page, item.to_page + 1))[:MAX_IMAGES])


def render_pages(item: Item, pages: dict[int, Page]) -> str:
    return "\n\n".join(f"[PDF p. {n}]\n{pages[n].full_text()}"
                       for n in range(item.from_page, item.to_page + 1) if n in pages)


def _minus_12m(ctx: RunContext) -> str:
    return (ctx.bid_due_date - relativedelta(months=12)).isoformat()
