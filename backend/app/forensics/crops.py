"""A cropped image of each finding's region, so calibration's report can be judged at a
glance (run.py calibrate-forensics)."""
from pathlib import Path

import pypdfium2 as pdfium

from app.forensics.finding import Finding

SCALE = 150 / 72          # 150 dpi: enough to see a figure's edges, small enough to keep
CONTEXT = (0.15, 0.03)    # shown around the region (fractions of the page): its neighbours


def save_crops(pdf: pdfium.PdfDocument, findings: list[Finding], folder: Path) -> None:
    """Writes one PNG per finding and sets its crop path; pages rendered once each."""
    folder.mkdir(parents=True, exist_ok=True)
    for page_no in sorted({f.page for f in findings}):
        image = pdf[page_no - 1].render(scale=SCALE).to_pil()
        width, height = image.size
        for f in (x for x in findings if x.page == page_no):
            r, (dx, dy) = f.region, CONTEXT
            box = (int(max(0.0, r["x"] - dx) * width), int(max(0.0, r["y"] - dy) * height),
                   int(min(1.0, r["x"] + r["w"] + dx) * width),
                   int(min(1.0, r["y"] + r["h"] + dy) * height))
            path = folder / f"{f.kind.lower()}-p{page_no}-{box[0]}-{box[1]}.png"
            image.crop(box).save(path)
            f.crop = str(path)
