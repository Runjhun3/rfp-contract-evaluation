# frontend

React UI for the bid evaluation service (React 19 + TypeScript + React Router,
built with Vite). Why React: ../docs/decisions.md D-025.

- `src/pages/` — one file per screen of the UI design: Projects, NewProject,
  OpenProject, RfpUpload, Criteria, Participants, RunProgress, Results,
  Evidence, NotFound.
- `src/components/` — shared pieces: the layout, project header + stepper,
  criteria table, firm picker, bid uploads, results table, evidence checks,
  decision form, loading/error states.
- `src/api.ts` — the only code that calls the Python API (`/api/v1`), including
  the CSRF header. `src/useApi.ts` loads a screen's data and polls where needed
  (criteria extraction every 10 s, run progress every 5 s).
- `src/styles/app.css` — all styling (design tokens at the top). No inline
  styles: the server's CSP forbids them.

```bash
npm install
npm run dev        # http://localhost:5173, proxies /api to python run.py web on :8000
npm run build      # type-check + build to dist/, served by `python run.py web`
npm test           # vitest unit tests
```
