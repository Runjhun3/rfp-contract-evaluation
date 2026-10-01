"""The scripted LLM of the end-to-end flow: answers each prompt from the page text,
the way the real model is asked to, so the flow runs without AWS."""
import json
import re
from pathlib import Path

DATA = Path(__file__).resolve().parents[3] / "data" / "golden" / "nsdf"
RFP, BID = DATA / "RFP_Document_NSDF.pdf", DATA / "Deloitte all docs.pdf"
SECTIONS = [(75, 181, "A.1"), (182, 250, "A.2"), (251, 334, "A.3")]

def label(user):
    out = []
    for n, body in re.findall(r"\[PDF p\. (\d+)\]\n(.*?)(?=\n\n\[PDF p\. |\Z)", user, re.S):
        n = int(n); head = body.strip()[:200]
        code = next((c for a, b, c in SECTIONS if a <= n <= b), None)
        row = {"pdf_page_no": n, "page_type": "OTHER",
               "eligibility": ["E.1"] if n == 1 else []}    # page 1 proves the requirement
        if re.search(r"Credential-\d+:", head) and code:
            row.update(page_type="PROJECT_HEADER", criterion_code=code, map_confidence=0.9, item_start=True)
        elif "Proposed CV for Program Manager" in head:
            row.update(page_type="CV", criterion_code="B.1", map_confidence=0.9, item_start=True)
        elif re.search(r"Proposed CV (of|for) Senior Consultant", head):
            row.update(page_type="CV", criterion_code="B.2", map_confidence=0.9, item_start=True)
        out.append(row)
    return json.dumps({"pages": out})

def item(user):
    code = re.search(r"Submitted under criterion: (\S+)", user).group(1)
    label_ = re.search(r"Item: (.+?) \(", user).group(1)
    first = re.search(r"\[PDF p\. (\d+)\]\n(.*?)\n", user, re.S)
    page, quote = int(first.group(1)), first.group(2).strip()[:60] or "x"
    marks = {"A.1": "2", "A.2": "2", "A.3": "2.5", "B.1": "8", "B.2": "7"}[code]
    return json.dumps({"label": label_, "code": code, "eligible": True, "marks": marks,
        "reason": "scripted", "confidence": 0.9, "relies_on": ["client"],
        "evidence": {"work_order": [page], "completion_or_ca": [page]},
        "facts": {"client": {"value": "c", "page": page, "quote": quote}}})

def criterion(user):
    mx = re.search(r"Max items: (\S+)\.", user).group(1); mx = int(mx) if mx.isdigit() else 99
    rows = json.loads(user.split("ITEM RESULTS\n", 1)[1])
    items = [dict(r, counted=i < mx) for i, r in enumerate(rows)]
    total = sum(float(r["marks"]) for r in items if r["counted"])
    return json.dumps({"code": re.search(r"criterion (\S+) for", user).group(1), "items": items,
                       "counted_items": min(len(rows), mx), "marks": str(total), "summary": "scripted"})


def eligibility(user):
    code = re.search(r"Requirement (\S+):", user).group(1)
    return json.dumps({"code": code, "result": "MET", "finding": "scripted", "facts": {}})


def fake(system, user, images=()):
    if "label pages" in system: return label(user)
    if "ELIGIBILITY CHECK" in user: return eligibility(user)
    if "Submitted under criterion" in user: return item(user)
    return criterion(user)


GOLD = json.load(open(Path(__file__).resolve().parents[1] / 'golden/nsdf/criteria.json'))["criteria"]
def extraction(user):
    rows = [dict(code=c["code"], parent=c["code"][0], stage="TECHNICAL", title=c["title"],
                 rfp_text="[verbatim clause]", meaning=c["meaning"], max_marks=c["max_marks"],
                 max_items=c["max_items"], kind=c["kind"], item_marks=c["allowed_item_marks"],
                 scored_by="LLM", rfp_page=34) for c in GOLD]
    rows.append(dict(code="C", stage="PRESENTATION", title="Technical presentation", rfp_text="[clause]",
                     meaning="Presentation and interview", max_marks="35", scored_by="COMMITTEE"))
    rows.append(dict(code="E.1", stage="ELIGIBILITY", title="EMD", rfp_text="[clause]", meaning="EMD paid"))
    return json.dumps({"criteria": rows})
def fake_all(system, user, images=()):
    return extraction(user) if "extract evaluation criteria" in system else fake(system, user)
