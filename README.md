# EduFlow

EduFlow is a student e-learning application built to demonstrate, with real test
evidence, conformance to the eight ISO/IEC 25010 software quality characteristics.
It combines a FastAPI/PostgreSQL backend, a React single-page frontend, and a
multi-layer automated test strategy (unit, API, end-to-end, performance, security
and portability).

A core rule of the project: no test result is claimed without evidence from an
actual execution. Observed results are recorded in `docs/traceability.md` and
`docs/iso25010-conformance.md` with pointers to the generated files in
`evidence/`; tools that could not run are documented as gaps.

## Team

| Member | Role |
| --- | --- |
| Houssem Amor | Lead / backend |
| Montaha KHEDHIRI | Frontend / UX |
| wissem ben slima | QA / tests |
| Oussema Ben Ayech | DevOps / documentation |

## Stack

| Layer | Technology |
| --- | --- |
| Backend | Python, FastAPI, SQLAlchemy, PostgreSQL, JWT authentication |
| Frontend | React, Vite, TypeScript |
| Tests | pytest + httpx, Playwright, Locust |
| Security | Bandit (SAST), pip-audit (SCA), OWASP ZAP (DAST) |
| Packaging | Docker, Docker Compose |
| CI | GitHub Actions (Python 3.14) |

## Quick start

The fastest way to run the whole stack is Docker Compose. From the repository
root:

```sh
docker compose up --build
```

The API is then available on `http://localhost:8000` and the frontend on
`http://localhost:5173`. See `docs/install.md` for manual setup, demo accounts
and troubleshooting.

## Documentation

- `docs/design.md` - architecture, data model, API, roles, business rules, OWASP mapping.
- `docs/traceability.md` - requirement to test to evidence matrix.
- `docs/iso25010-conformance.md` - per-characteristic quality requirements and evidence.
- `docs/install.md` - reproducible install and run guide.
- `docs/demo.md` - soutenance checklist: three role walkthroughs plus the two test layers demonstrated live; rehearsal output in `evidence/demo-check.txt`.

## Test commands

Commands are run from the repository root unless noted.

```sh
# Unit + API + integration + reliability + fuzz + smoke with coverage
pytest --cov=app --cov-report=html:evidence/coverage --junitxml=evidence/api.xml tests

# End-to-end (Chromium + Firefox) and axe-core accessibility scan
# Requires the stack running; E2E_BASE_URL defaults to http://localhost:5173
pytest tests/e2e -m e2e --junitxml=evidence/e2e.xml

# Real-browser CDP simulation of the three role dashboards (Chrome/Edge, or CHROME_PATH)
pytest tests/e2e/test_dashboard_simulation.py -m simulation -q

# Static application security testing
bandit -r app -f txt -o evidence/bandit.txt

# Dependency vulnerability scans
pip-audit -r requirements.txt -f columns > evidence/pip-audit.txt
npm audit --prefix frontend > evidence/npm-audit.txt

# Load test (writes both text and CSV output)
locust -f tests/performance/locustfile.py --headless -u 20 -r 5 -t 30s \
  --host http://localhost:8000 --csv=evidence/perf > evidence/performance.txt

# Dynamic application security scan (requires the ZAP container image)
docker run --rm -v "<absolute path>/evidence:/zap/wrk:rw" \
  ghcr.io/zaproxy/zaproxy:stable zap-baseline.py \
  -t http://host.docker.internal:8000 -r zap.html -J zap.json

# Validate and exercise the container definition
docker compose config > evidence/docker-compose-config.txt
docker compose up --build -d

# Complexity and maintainability metrics
python -m radon cc app -a -s > evidence/complexity.txt
python -m radon mi app >> evidence/complexity.txt
python -m radon raw app >> evidence/complexity.txt

# Rehearse the soutenance (app + two live test layers)
powershell -File tools/demo_check.ps1

# Regenerate charts and the EN/FR reports from the evidence
python tools/generate_charts.py
python tools/generate_reports.py
```

## Test toolkit: what each test does and how to read its result

The table below maps every test/check to the tool that runs it, the behaviour it
verifies, and the meaning of the result recorded in `evidence/`.

| Test / check | Tool | What it verifies | What the recorded result means |
| --- | --- | --- | --- |
| Unit - business rules | pytest 9.0.3 (`tests/unit/`) | The eight documented rules BR1..BR8 in the service layer: unique email, unique enrollment, seat capacity, ownership/roles, completion date, no delete with validated enrollments, audit writes, password/JWT strength. | **9 passed, 0 failed**: every rule is enforced in isolation and its negative case is rejected with the expected error. |
| API contract | pytest + httpx/TestClient (`tests/api/`) | Status codes, response shape, pagination envelope, validation errors, 401 on bad tokens, 403 on cross-role access, 404 on unknown ids. | **8 passed**: the HTTP interface behaves as documented; auth and RBAC denials are real, not UI-only. |
| Integration flows | pytest + httpx (`tests/integration/`) | CRUD on users, courses, sessions, tags and enrollments; workflow transitions; dashboard metrics; audit entries. | **8 passed**: API requests and database state stay consistent across complete flows. |
| Reliability | pytest (`tests/reliability/`) | Duplicate submits, rejected transitions leaving state unchanged, no secrets in logs, and a threaded double-enroll race. | **4 passed**: failures and concurrency do not corrupt data; the unique constraint converts the race into a 409 instead of a duplicate row or a 500. |
| Fuzz / property-based | Hypothesis (`tests/fuzz/`) | Generated invalid emails, titles, capacities, tokens and search strings; password hash round-trips. | **6 tests, 300+ generated examples, 0 failures**: adversarial input never crashes a schema or makes the API return 500. |
| Smoke | pytest (`tests/smoke/`) | All three demo accounts can log in and the core endpoints answer after a deployment. | **5 passed**: the deployed application is usable, not just buildable. |
| End-to-end | Playwright, Chromium + Firefox (`tests/e2e/test_ui.py`) | Learner, admin and formateur journeys: search, dashboard, audit, users, RBAC guards, logout. | **8 passed (4 journeys x 2 browsers)**: the UI works in both engines, not only the development browser. |
| Accessibility | axe-core via Playwright (`test_accessibility.py`) | WCAG 2.0 A/AA violations on login and dashboard screens. | **0 violations at final run**: two earlier serious color-contrast findings were fixed; this is the configured rule set, not a full manual audit. |
| Dashboard simulation | `automation_engine.py` + Playwright `connect_over_cdp` (`test_dashboard_simulation.py`) | Real installed browser (Edge here) visiting each role's dashboard and role-specific windows via CDP. | **1 passed, 9 screenshots, 0 page errors**: all three roles reach the correct windows and admin-only navigation is hidden from non-admins. |
| Performance | Locust (`tests/performance/locustfile.py`) | 20 concurrent users issuing login, courses, enrollments, dashboard and audit requests for 30 s. | **940 requests, 0 failures; aggregated p50 7 ms / p95 17 ms; login p95 97 ms**: all endpoints are below the 500 ms target at p95. p95 means 95% of requests were faster than that value. |
| Coverage | pytest-cov | Share of application lines executed by the non-browser tests. | **88%** (>= 80% target): most code paths are exercised; the remaining lines are mostly error branches. |
| SAST | Bandit | Insecure source patterns (hardcoded secrets, weak crypto, unsafe calls). | **0 issues over 872 lines**: no pattern from Bandit's rule set was found; this is not a proof of absence of all bugs. |
| Python SCA | pip-audit | Published CVEs in pinned Python dependencies. | **0 known vulnerabilities** after pytest was upgraded to 9.0.3. |
| Frontend SCA | npm audit | Published CVEs in frontend npm dependencies. | **0 vulnerabilities** after Vite/react-router upgrades. |
| DAST | OWASP ZAP baseline | The running app for injections, missing headers and other live response issues. | **0 new failures, 67 checks passed, 1 informational alert** (cacheable 404s): no high/medium finding from the baseline rule set. |
| Portability | Docker Compose | Reproducible install from the committed definitions. | **valid config + 3 healthy containers + HTTP 200** on API and UI: a clean machine can run the stack from the repository. |

A result is only claimed when the matching file in `evidence/` contains the
raw output. Counts of zero mean "none found by that tool's rule set at that
time", not a mathematical guarantee that no defect exists.

## Evidence location

Raw reports are committed under `evidence/` (JUnit XML, coverage HTML/XML,
Bandit, pip-audit, npm audit, ZAP HTML/JSON, axe JSON, Locust text/CSV, Docker
Compose validation and live-stack checks). `evidence/charts/` holds graphs
generated from those raw files and embedded in the PDF reports. The traceability
matrix maps every requirement to the exact evidence file; no result in the
documentation is claimed without a corresponding execution artifact.

## Generating the design reports

```sh
python tools/generate_reports.py
```

This writes `reports/Design_Report_EN.docx/.pdf` and
`reports/Rapport_de_Conception_FR.docx/.pdf` from the Markdown documentation and
the real evidence. Each report includes an observed-results table and the three
charts generated by `tools/generate_charts.py` (p95 latency vs the 500 ms target,
per-module coverage vs the 80% target, and tests executed by test / check).
