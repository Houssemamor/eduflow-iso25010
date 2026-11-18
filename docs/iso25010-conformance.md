# EduFlow ISO/IEC 25010 Conformance Report

Execution date: 2026-11-18. All results below reference files in `evidence/`
produced by actual tool runs. No result is simulated. Charts generated from the
raw evidence are in `evidence/charts/` and are embedded in the EN/FR PDF reports.

## Q1 - Functional suitability

- **Concrete requirement:** all section 4 features are implemented and behave as
  specified (authentication and RBAC, CRUD on related entities, workflow,
  dashboard, search, audit, business rules).
- **Test / tool:** pytest (unit, integration, API, fuzz, smoke, reliability) and
  Playwright.
- **Evidence:** `evidence/unit.xml` (9 passed), `evidence/api.xml` (31 passed),
  `evidence/e2e.xml` (9 passed).
- **Result:** Passed. 49 automated tests executed.

## Q2 - Performance efficiency

- **Concrete requirement:** response time measured under load; target below
  500 ms with 20 concurrent users.
- **Test / tool:** Locust headless, 20 users, spawn rate 5, 30 s, against the
  containerized API; text and CSV output retained.
- **Evidence:** `evidence/performance.txt`, `evidence/perf_stats.csv`,
  `evidence/charts/performance_p95.png`.
- **Result:** Passed. 940 requests, 0 failures. Aggregated p50 7 ms, p95 17 ms.
  Login p50 76 ms, p95 97 ms. All endpoints, including login, are below the
  500 ms target at p95. The chart draws the 500 ms target line for comparison.

## Q3 - Compatibility

- **Concrete requirement:** the application works on at least two browsers,
  Chromium and Firefox, and in a containerized deployment.
- **Test / tool:** the same four Playwright journeys run in both engines; the
  stack is deployed with Docker Compose.
- **Evidence:** `evidence/e2e.xml`, `evidence/docker-compose-up.txt`,
  `evidence/docker-stack-verification.txt`.
- **Result:** Passed. 8/8 browser tests passed (4 journeys x 2 browsers); all
  three Compose containers reached healthy/running state and served HTTP 200.

## Q4 - Usability

- **Concrete requirement:** user journeys are validated and WCAG 2.0 A/AA
  violations are detected automatically.
- **Test / tool:** Playwright journeys plus an axe-core scan of the login and
  dashboard screens (Chromium).
- **Evidence:** `evidence/e2e.xml`, `evidence/axe.json`, `evidence/e2e-*.png`.
- **Result:** Passed after remediation. The first axe run reported a serious
  `color-contrast` violation on the demo-credential code chips (3.86:1) and a
  muted-text violation on the dashboard (4.34:1). Both CSS colors were darkened
  and the final scan reports 0 violations.

## Q5 - Reliability

- **Concrete requirement:** consistent behavior on errors: no duplicate rows on
  repeated or concurrent requests, no state change on a rejected transition, no
  secrets in security logs.
- **Test / tool:** dedicated pytest reliability and concurrency scenarios. The
  unique(user, course) constraint plus an `IntegrityError` handler form the
  final guard against a concurrent double-submit.
- **Evidence:** `evidence/api.xml`.
- **Result:** Passed. 4 reliability/concurrency scenarios passed.

## Q6 - Security

- **Concrete requirement:** robust authentication, role-based access control and
  no known vulnerabilities (OWASP Top 10 2025).
- **Test / tool:** Bandit (SAST), pip-audit (Python SCA), npm audit (frontend
  SCA), OWASP ZAP baseline (DAST), negative RBAC tests.
- **Evidence:** `evidence/bandit.txt`, `evidence/pip-audit.txt`,
  `evidence/npm-audit.txt`, `evidence/zap.html`, `evidence/zap.json`,
  `evidence/api.xml`.
- **Result:** Passed. Bandit: 0 issues over 872 lines. pip-audit: 0 known
  vulnerabilities after upgrading pytest to 9.0.3. npm audit: 0 vulnerabilities
  after upgrading Vite to 8.3.8 and react-router-dom to 7.18.6. ZAP: 0 new
  failures, 67 checks passed, 1 informational alert (Storable and Cacheable
  Content on 404 responses). Negative tests confirm 401 on invalid tokens and
  403 on cross-role access.

## Q7 - Maintainability

- **Concrete requirement:** layered code, controlled complexity and measured
  coverage of at least 80%.
- **Test / tool:** pytest-cov coverage run, Bandit, module-level coverage chart.
- **Evidence:** `evidence/coverage/index.html`, `evidence/coverage.xml`,
  `evidence/charts/coverage_by_module.png`, `evidence/bandit.txt`.
- **Result:** Passed. Total line coverage 88% (607 statements, 73 missed). Code
  is split into config, db, models, schemas, security, services and API layers.

## Q8 - Portability

- **Concrete requirement:** reproducible installation on another machine via a
  documented container definition.
- **Test / tool:** `docker compose config` validation, `docker compose up
  --build -d`, live HTTP checks against the running containers.
- **Evidence:** `evidence/docker-compose-config.txt`,
  `evidence/docker-compose-up.txt`, `evidence/docker-stack-verification.txt`.
- **Result:** Passed. Compose configuration resolves without errors; PostgreSQL,
  backend and frontend containers were built and started. The API returned a
  valid JWT, 3 seeded courses, dashboard metrics and audit entries; the frontend
  served HTTP 200.

## Dashboard navigation simulation (Part II of the reports)

A real installed browser is detected by `automation_engine.py` using this
resolution order: `CHROME_PATH` override, Google Chrome (machine x86/x64 and
per-user), Microsoft Edge (machine x64/x86 and per-user), then executables on
PATH. On this host the resolved browser was **msedge.exe** at
`%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe`.

The browser is launched with CDP flags (`--remote-debugging-port=9222`,
`--user-data-dir=<temp profile>`, `--no-first-run`,
`--no-default-browser-check`, WebRTC privacy flags, `--start-maximized`) and
driven through `connect_over_cdp` by `tests/e2e/test_dashboard_simulation.py`.
Each of the three roles logs in and visits its own dashboard and role-specific
windows:

- **admin**: dashboard, users, audit log (admin-only navigation visible);
- **formateur**: dashboard, courses, enrollments;
- **apprenant**: dashboard, courses, enrollments (admin navigation absent).

Every window is asserted by a stable `data-testid` and captured as a full-page
screenshot. Evidence: `evidence/dashboard_tour.json` (trace, browser, zero page
errors) and `evidence/dashboard_tour_<role>_<n>_<window>.png` (9 screenshots).
All nine screenshots are reproduced in **Part II** of both EN and FR reports.
The browser is not launched from an HTTP endpoint: that would expose remote
process execution, so the harness runs locally only.

## Graphs

- `evidence/charts/performance_p95.png` - p95 response time per endpoint with
  the 500 ms target line (Q2).
- `evidence/charts/coverage_by_module.png` - line coverage per module with the
  80% target line (Q7).
- `evidence/charts/tests_by_layer.png` - number of tests executed per layer
  (Q1).

All three charts are generated by `tools/generate_charts.py` from the raw JUnit
XML, coverage XML and Locust CSV, and are embedded in both PDF reports.
