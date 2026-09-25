"""Serves the built React app (frontend/dist). Any non-API path gets index.html,
so React Router can show the right screen on a reload or a pasted link.
"""
from pathlib import Path

from starlette.responses import FileResponse, HTMLResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from app.web.common import fail

DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"   # repo-root/frontend/dist

NOT_BUILT = ("<!doctype html><title>Bid Evaluation</title><p>The UI is not built yet. "
             "Run <code>npm install</code> and <code>npm run build</code> in "
             "<code>frontend/</code>, or use <code>npm run dev</code> during development.</p>")


async def index(request):
    if request.path_params["path"].startswith("api/"):
        return fail("Not found", 404)
    page = DIST / "index.html"
    if not page.exists():
        return HTMLResponse(NOT_BUILT, status_code=503)
    return FileResponse(page, headers={"Cache-Control": "no-cache"})


def routes() -> list:
    assets = [Mount("/assets", StaticFiles(directory=str(DIST / "assets")), name="assets")] \
        if (DIST / "assets").is_dir() else []
    return [*assets, Route("/{path:path}", index, methods=["GET"])]
