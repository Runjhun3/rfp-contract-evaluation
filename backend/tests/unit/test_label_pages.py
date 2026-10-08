import json

from app.config import Settings
from app.ingest.label_pages import BATCH_SIZE, NO_PAGES_BEFORE, label_pages
from app.llm.client import LlmClient
from app.schemas.records import Page

# A made-up bid: a project's header on p.18, its certificate on p.19-20, the next batch
# opening on p.21.
PAGES = [Page(pdf_page_no=n, text=f"Page {n} of a hypothetical bid") for n in range(1, 24)]
FIRST = {18: ("PROJECT_HEADER", True, "Hypothetical stadium PMU"),
         19: ("COMPLETION_CERT", False, None), 20: ("COMPLETION_CERT", False, None)}


def labels(numbers, types) -> str:
    return json.dumps({"pages": [{"pdf_page_no": n, "page_type": types.get(n, ("OTHER",))[0],
                                  "item_start": types.get(n, ("", False))[1],
                                  "title": types.get(n, ("", False, None))[2]}
                                 for n in numbers]})


def test_each_batch_sees_the_pages_before_it_with_their_labels_but_never_relabels_them(
        tmp_path):
    calls = []

    def fake(system, user, images):
        calls.append(user)
        if len(calls) == 1:
            return labels(range(1, BATCH_SIZE + 1), FIRST)
        # The second batch's reply also (wrongly) labels a page of PAGES BEFORE.
        return labels([20, 21, 22, 23], {20: ("PROJECT_HEADER", True, "Wrong"),
                                         21: ("PROJECT_HEADER", True, "Next PMU")})

    llm = LlmClient(Settings(_env_file=None, llm_cache_dir=str(tmp_path)), completer=fake)
    pages = {p.pdf_page_no: p for p in label_pages([p.model_copy() for p in PAGES], [], llm, [])}
    assert NO_PAGES_BEFORE in calls[0]
    before = calls[1].split("PAGES BEFORE (context only)")[1].split("\nPAGES\n")[0]
    assert "[PDF p. 18] (labelled PROJECT_HEADER, first page of: Hypothetical stadium PMU)" \
        in before
    assert "[PDF p. 20] (labelled COMPLETION_CERT)" in before and "[PDF p. 17]" not in before
    assert "[PDF p. 21]" not in before
    assert (pages[20].page_type, pages[20].item_start) == ("COMPLETION_CERT", False)
    assert (pages[21].page_type, pages[21].title) == ("PROJECT_HEADER", "Next PMU")
