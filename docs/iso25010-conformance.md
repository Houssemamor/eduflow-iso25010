# EduFlow ISO/IEC 25010 Conformance Report

Execution date: 2026-11-18. All results below reference files in `evidence/`
produced by actual tool runs. No result is simulated. Where a tool could not be
executed, the gap and the exact reproduction procedure are recorded.

## Q1 - Functional suitability

- **Concrete requirement:** all section 4 features are implemented and behave as
  specified (authentication and RBAC, CRUD on related entities, workflow,
  dashboard, search, audit, business rules).
- **Test / tool:** pytest (unit, integration, API, reliability) and Playwright.
- **Evidence:** `evidence/unit.xml` (9 passed), `evidence/api.xml` (19 passed),
  `evidence/e2e.xml` (8 passed).
- **Result:** Passed. 36 automated tests executed.

## Q2 - Performance efficiency

- **Concrete requirement:** response time measured under load; target below
  500 ms with 20 concurrent users.
- **Test / tool:** Locust headless, 20 users, spawn rate 5, 30 s, against the
  running API.
- **Evidence:** `evidence/performance.txt`.
- **Result:** 911 requests, 0 failures. Aggregated response time p50 6 ms,
  p95 190 ms. Read endpoints (courses, enrollments, dashboard, audit) stay below
  the target at p95. Login p50 490 ms and p95 810 ms (bcrypt hashing); the tail
  exceeds the target and is recorded as a partial result rather than a pass.
  Password hashing rounds were reduced from the default to the OWASP minimum of
  10 to keep median login latency under 500 ms.

## Q3 - Compatibility

- **Concrete requirement:** the application works on at least two browsers,
  Chromium and Firefox.
- **Test / tool:** the same four Playwright journeys run in both engines.
- **Evidence:** `evidence/e2e.xml`.
- **Result:** Passed. 8/8 browser tests passed (4 journeys x 2 browsers).

## Q4 - Usability

- **Concrete requirement:** user journeys are validated and basic accessibility
  (labels, semantic controls, keyboard operation) is present.
- **Test / tool:** Playwright journeys plus semantic HTML with `<label>` for
  every form control and visible focus styles.
- **Evidence:** `evidence/e2e.xml`, `evidence/e2e-*.png`.
- **Result:** Passed for journeys and baseline controls. No automated axe scan
  was run; accessibility is limited to the baseline above and is stated as such.

## Q5 - Reliability

- **Concrete requirement:** consistent behavior on errors: no duplicate rows on
  repeated requests, no state change on a rejected transition, no secrets in
  security logs.
- **Test / tool:** dedicated pytest reliability scenarios.
- **Evidence:** `evidence/api.xml`.
- **Result:** Passed. 3 reliability scenarios passed.

## Q6 - Security

- **Concrete requirement:** robust authentication, role-based access control and
  no known source or dependency vulnerabilities (OWASP Top 10 2025).
- **Test / tool:** Bandit (SAST), pip-audit (SCA), negative RBAC tests.
- **Evidence:** `evidence/bandit.txt`, `evidence/pip-audit.txt`,
  `evidence/api.xml`.
- **Result:** Bandit scanned 872 lines with zero issues. pip-audit reported no
  known vulnerabilities after pytest was upgraded from 8.3.4 to 9.0.3. Negative
  tests confirm 401 on invalid tokens and 403 on cross-role access. OWASP ZAP
  DAST could not be executed here; the gap and procedure are documented below.

## Q7 - Maintainability

- **Concrete requirement:** layered code, controlled complexity and measured
  coverage of at least 80%.
- **Test / tool:** pytest-cov coverage run and Bandit.
- **Evidence:** `evidence/coverage/index.html`, `evidence/coverage.xml`,
  `evidence/bandit.txt`.
- **Result:** Passed. Total coverage 88% (607 statements, 73 missed). Code is
  split into config, db, models, schemas, security, services and API layers.

## Q8 - Portability

- **Concrete requirement:** reproducible installation on another machine via a
  documented container definition.
- **Test / tool:** `docker compose config` and `docs/install.md`.
- **Evidence:** `evidence/docker-compose-config.txt`.
- **Result:** Passed. Compose configuration resolves without errors. The image
  builds from pinned dependencies and runs as a non-root user.

## Tool availability notes

- **OWASP ZAP (DAST) - unavailable:** the scanner is not installed on the host,
  and `docker pull ghcr.io/zaproxy/zaproxy:stable` failed in this environment.
  Procedure on a machine with registry access: pull the image, start the stack,
  run the baseline scan against `http://localhost:8000` and save the report to
  `evidence/zap.html`. The DAST result is therefore reported as unavailable, not
  as a pass. SAST, SCA and negative RBAC tests cover the remaining security
  evidence.
- **Accessibility tooling:** no axe/DevTools scan was executed; only the
  baseline semantic checks described in Q4 are claimed.
