# EduFlow Frontend

Frontend for the EduFlow e-learning management application. Built with Vite, React 18, and TypeScript (strict mode), with plain responsive CSS and no UI kit or chart library.

## Prerequisites

- Node.js 18 or newer
- npm
- The EduFlow backend running on `http://localhost:8000` (all API routes are prefixed with `/api/v1`)

## Run locally

```bash
cd frontend
npm install
npm run dev
```

The dev server starts on `http://localhost:5173`. Requests to `/api` are proxied to the backend at `http://localhost:8000`, so no CORS setup is needed during development.

## Other scripts

```bash
npm run build      # Type-check and produce a production build in dist/
npm run preview    # Serve the production build locally
npm run typecheck  # TypeScript strict type-check only
```

## Roles and routes

| Route | Access | Purpose |
| --- | --- | --- |
| `/login` | Public | Sign in with email and password |
| `/dashboard` | All roles | Metrics and CSS-based visualizations with filters |
| `/courses` | All roles | Course catalogue; CRUD for admin/formateur |
| `/sessions` | All roles | Session schedule; CRUD for admin/formateur |
| `/enrollments` | All roles | Enrollment lifecycle with role-dependent actions |
| `/users` | Admin only | User and role management |
| `/tags` | Admin only | Course tag management |
| `/audit` | Admin only | Audit event table |
| `/access-denied` | Authenticated | Shown when a role gate blocks a route |

Demo accounts follow the pattern `admin@eduflow.local`, `formateur@eduflow.local`, and `apprenant@eduflow.local`. Use the password provided with your environment setup.

## Testing hooks

Key interactive elements and table rows expose `data-testid` attributes (for example `login-submit`, `nav-courses`, `course-create`, `course-row-<id>`, `enrollment-validate-<id>`, `logout-button`) for Playwright end-to-end tests.

## Notes

- The access token is stored in `localStorage` under `eduflow_access_token` and sent as `Authorization: Bearer <token>` on every request except login.
- A `401` response clears the stored session and redirects the user to the login screen.
- Forms use native HTML validation plus explicit error displays; all controls have associated labels and visible focus states.
