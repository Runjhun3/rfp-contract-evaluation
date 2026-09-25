"""The web app: a JSON API under /api/v1 plus the built React UI (frontend/dist).

Run: python run.py web   (uvicorn on 127.0.0.1:8000; put nginx with TLS in front)
During UI development run `npm run dev` in frontend/ as well; Vite proxies /api here.
"""
import json
import secrets

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import Settings
from app.web import (routes_bids, routes_criteria, routes_evidence, routes_projects,
                     routes_results, routes_runs, spa)
from app.web.auth import Forbidden
from app.web.common import fail

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; img-src 'self'; style-src 'self'; "
                               "script-src 'self'; frame-ancestors 'none'; form-action 'self'",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
}


class SecurityHeaders:
    def __init__(self, app, secure: bool):
        self.app, self.secure = app, secure

    async def __call__(self, scope, receive, send):
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                extra = dict(SECURITY_HEADERS)
                if self.secure:
                    extra["Strict-Transport-Security"] = "max-age=31536000"
                headers += [(k.lower().encode(), v.encode()) for k, v in extra.items()]
            await send(message)
        await self.app(scope, receive, send_with_headers)


async def _forbidden(request, exc):
    return fail("Your session expired. Reload the page and try again.", 403)


async def _bad_json(request, exc):
    return fail("The request body is not valid JSON.", 400)


async def _not_found(request, exc):
    return fail("Not found", 404)


def create_app(settings: Settings) -> Starlette:
    # The session only carries the CSRF token, so a fresh key per start is fine.
    session_secret = settings.session_secret or secrets.token_urlsafe(32)
    routes = [*routes_projects.routes, *routes_criteria.routes, *routes_bids.routes,
              *routes_runs.routes, *routes_results.routes, *routes_evidence.routes,
              *spa.routes()]
    middleware = [
        Middleware(SecurityHeaders, secure=settings.cookie_secure),
        Middleware(SessionMiddleware, secret_key=session_secret,
                   https_only=settings.cookie_secure, same_site="strict", max_age=8 * 3600),
    ]
    app = Starlette(routes=routes, middleware=middleware, exception_handlers={
        Forbidden: _forbidden, json.JSONDecodeError: _bad_json, 404: _not_found})
    app.state.settings = settings
    return app
