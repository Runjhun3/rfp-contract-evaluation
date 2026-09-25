# frontend

Server-rendered UI for the bid evaluation service. No build step, no node.

- `templates/` — Jinja2 pages, one per screen of the UI design (base.html is the shared shell).
- `static/app.css` — all styling (design tokens at the top).
- `static/app.js` — small enhancements: live run progress, auto-refresh, override box.

The server that fills these pages lives in `backend/app/web/` (routes, auth, CSRF).
Run it with `cd backend && python run.py web`.
