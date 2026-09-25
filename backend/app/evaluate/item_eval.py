"""EVAL_ITEM: one LLM call per item (project section or CV), one criterion."""
from dateutil.relativedelta import relativedelta

from app.llm.client import LlmClient
from app.llm.prompts import fill, load
from app.schemas.llm import ItemResult
from app.schemas.records import Item, Page, RunContext


def system_prompt(ctx: RunContext, criteria_block: str) -> str:
    minus_12m = _minus_12m(ctx)
    rules = fill(load("system"), department=ctx.department,
                 bid_due_date=ctx.bid_due_date.isoformat(), bid_due_minus_12m=minus_12m)
    return f"{rules}\n{fill(criteria_block, bid_due_minus_12m=minus_12m)}"


def evaluate_item(item: Item, pages: dict[int, Page], ctx: RunContext, system: str,
                  llm: LlmClient) -> ItemResult:
    user = fill(load("item"), bidder=ctx.bidder, label=item.label, kind=item.kind,
                code=item.criterion_code, pages=render_pages(item, pages))
    result = llm.ask_json(system, user, ItemResult)
    result.label, result.code = item.label, item.criterion_code
    return result


def render_pages(item: Item, pages: dict[int, Page]) -> str:
    return "\n\n".join(f"[PDF p. {n}]\n{pages[n].full_text()}"
                       for n in range(item.from_page, item.to_page + 1) if n in pages)


def _minus_12m(ctx: RunContext) -> str:
    return (ctx.bid_due_date - relativedelta(months=12)).isoformat()
