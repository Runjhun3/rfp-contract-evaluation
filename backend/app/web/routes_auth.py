"""Sign in / sign out."""
from starlette.routing import Route

from app.db import q_projects
from app.db.connection import transaction
from app.web import auth
from app.web.common import go, templates


async def home(request):
    return go("/projects")


async def login_page(request):
    return templates.TemplateResponse(request, "login.html", {"request": request, "user": None,
                                                              "error": None, "email": ""})


async def login_submit(request):
    form = await request.form()
    email, password = str(form.get("email", "")).strip(), str(form.get("password", ""))
    with transaction(request.app.state.settings) as cur:
        user = q_projects.user_by_email(cur, email)
    if user is None or not auth.verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(
            request, "login.html", {"request": request, "user": None, "email": email,
                                    "error": "Email or password is not right."}, status_code=400)
    auth.login(request, user["user_id"])
    return go("/projects")


async def logout(request):
    await auth.form_with_csrf(request)
    request.session.clear()
    return go("/login")


routes = [Route("/", home), Route("/login", login_page, methods=["GET"]),
          Route("/login", login_submit, methods=["POST"]),
          Route("/logout", logout, methods=["POST"])]
