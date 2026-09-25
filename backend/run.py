"""Command line entry point (phase 1).

  python run.py evaluate --bid BID.pdf --bidder Deloitte --tender GEM/2026/B/7401395 \
      --department "Department of Sports, MYAS" --bid-date 2026-05-07 \
      --criteria tests/golden/nsdf/criteria.json --block tests/golden/nsdf/criteria_block.md \
      --out runs/nsdf/deloitte
  python run.py compare --run runs/nsdf/deloitte --bidder Deloitte \
      --expected tests/golden/nsdf/expected_scores.json
  python run.py migrate                      # apply backend/migrations/*.sql
  python run.py web                          # the UI on http://127.0.0.1:8000
  python run.py worker                       # background jobs (run alongside web)
  python run.py save-run --run runs/nsdf/deloitte --project "NSDF PMU 2026"
"""
import argparse
from datetime import date
from pathlib import Path

from app.config import get_settings


def main() -> None:
    args = _parser().parse_args()
    if args.command == "evaluate":
        _evaluate(args)
    elif args.command == "migrate":
        from app.db.migrate import migrate
        print("applied:", migrate(get_settings()) or "nothing, database is up to date")
    elif args.command == "web":
        import uvicorn
        from app.web.app import create_app
        uvicorn.run(create_app(get_settings()), host=args.host, port=int(args.port),
                    proxy_headers=True)
    elif args.command == "worker":
        import logging
        from app.jobs.worker import forever
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
        forever(get_settings())
    elif args.command == "save-run":
        from app.db.save_run import save_run
        print("saved run", save_run(get_settings(), Path(args.run), args.project))
    else:
        from app.compare import compare
        report = compare(Path(args.run), Path(args.expected), args.bidder)
        (Path(args.run) / "comparison.md").write_text(report, encoding="utf-8")
        print(report)


def _evaluate(args: argparse.Namespace) -> None:
    from app.criteria import load_block, load_criteria
    from app.llm.client import LlmClient
    from app.pipeline import run
    from app.schemas.records import RunContext

    settings = get_settings()
    ctx = RunContext(tender_no=args.tender, department=args.department, bidder=args.bidder,
                     bid_due_date=date.fromisoformat(args.bid_date))
    scores = run(Path(args.bid), ctx, load_criteria(Path(args.criteria)),
                 load_block(Path(args.block)), Path(args.out), settings, LlmClient(settings))
    for s in scores:
        flag = f"  REVIEW: {', '.join(s.review_reasons)}" if s.needs_review else ""
        print(f"{s.code}: LLM {s.llm_marks} | checked {s.checked_marks}{flag}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RFP bid evaluation (phase 1)")
    sub = parser.add_subparsers(dest="command", required=True)
    ev = sub.add_parser("evaluate", help="score one bidder")
    for name in ("--bid", "--bidder", "--tender", "--department", "--bid-date",
                 "--criteria", "--block", "--out"):
        ev.add_argument(name, required=True)
    cmp = sub.add_parser("compare", help="compare a run with the committee sheet")
    for name in ("--run", "--bidder", "--expected"):
        cmp.add_argument(name, required=True)
    sub.add_parser("migrate", help="apply pending SQL migrations")
    web = sub.add_parser("web", help="run the UI")
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", default="8000")
    sub.add_parser("worker", help="run background jobs")
    save = sub.add_parser("save-run", help="load a finished run folder into Postgres")
    for name in ("--run", "--project"):
        save.add_argument(name, required=True)
    return parser


if __name__ == "__main__":
    main()
