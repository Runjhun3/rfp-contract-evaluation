"""API: named sign-in accounts, for administrators only (see app/users.py)."""
from starlette.routing import Route

from app import users
from app.db.connection import transaction
from app.web.auth import check_csrf, current_user, is_admin
from app.web.common import fail, ok

ADMINS_ONLY = "Only an administrator can manage accounts."


def _db(request):
    return transaction(request.app.state.settings)


def _done(problem: str | None, message: str, status_code: int = 200):
    if problem:
        return fail(problem, 404 if problem == users.NOT_FOUND else 400)
    return ok(None, message, status_code)


async def list_users(request):
    if not is_admin(request):
        return fail(ADMINS_ONLY, 403)
    with _db(request) as cur:
        return ok(users.overview(cur))


async def create_user(request):
    check_csrf(request)
    if not is_admin(request):
        return fail(ADMINS_ONLY, 403)
    body = await request.json()
    with _db(request) as cur:
        problem = users.create(cur, body, current_user(request),
                               request.app.state.settings.app_username)
    return _done(problem, "Account created", 201)


async def set_active(request):
    check_csrf(request)
    if not is_admin(request):
        return fail(ADMINS_ONLY, 403)
    body = await request.json()
    with _db(request) as cur:
        problem = users.set_active(cur, str(request.path_params["user_id"]),
                                   bool(body.get("active")), current_user(request))
    return _done(problem, "Account updated")


async def set_password(request):
    check_csrf(request)
    if not is_admin(request):
        return fail(ADMINS_ONLY, 403)
    body = await request.json()
    with _db(request) as cur:
        problem = users.reset_password(cur, str(request.path_params["user_id"]),
                                       str(body.get("password") or ""), current_user(request))
    return _done(problem, "Password set")


routes = [
    Route("/api/v1/users", list_users, methods=["GET"]),
    Route("/api/v1/users", create_user, methods=["POST"]),
    Route("/api/v1/users/{user_id:uuid}/active", set_active, methods=["POST"]),
    Route("/api/v1/users/{user_id:uuid}/password", set_password, methods=["POST"]),
]
