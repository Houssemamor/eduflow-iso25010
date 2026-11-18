# EduFlow Traceability Matrix

This matrix links every functional requirement (FR) and quality characteristic
(Q) from the cahier des charges to its test, tool, evidence file and observed
status. A result is recorded only after a real execution produced the referenced
evidence file; unavailable tools are marked as gaps, never simulated.

Functional requirements FR1..FR7 are derived from section 4 of the cahier des
charges. Quality requirements Q1..Q8 map to the eight ISO/IEC 25010
characteristics in section 6.

## Functional requirements

| Requirement ID | Description | Type | Test(s) | Tool(s) | Evidence path | Status |
| --- | --- | --- | --- | --- | --- | --- |
| FR1 | Authentication and role management with three distinct profiles (admin, formateur, apprenant) and differentiated rights. | functional | `tests/integration/test_api_flows.py::test_login_and_me`, `::test_users_crud_and_rbac`, `tests/api/test_contract.py::test_unauthenticated_is_401`, `::test_invalid_token_is_401`, `::test_admin_endpoints_deny_learner`, `tests/smoke/test_smoke.py` | pytest, httpx | evidence/api.xml | Passed - 31 API-layer tests |
| FR2 | At least four related business entities (User, Course, Session, Enrollment, plus Tag) with full CRUD and real 1-N and N-N relations. | functional | `tests/integration/test_api_flows.py` (course, session, user, tag lifecycles), `tests/unit/test_business_rules.py::test_br2_unique_user_course_enrollment` | pytest, httpx | evidence/unit.xml, evidence/api.xml | Passed |
| FR3 | Status workflow (pending -> validated -> completed, cancellable) with enforced transition rules. | functional | `tests/unit/test_business_rules.py::test_workflow_allowed_transitions`, `::test_br3_capacity_checked_at_validation`, `::test_br5_completion_only_after_session_end`, `tests/reliability/test_reliability.py::test_failed_transition_leaves_state_unchanged` | pytest | evidence/unit.xml, evidence/api.xml | Passed |
| FR4 | Dashboard with aggregated indicators and filters. | functional | `tests/integration/test_api_flows.py::test_full_course_lifecycle`, `::test_dashboard_and_audit_filters`, `tests/e2e/test_ui.py::test_formateur_dashboard_metrics` | pytest, Playwright | evidence/api.xml, evidence/e2e.xml, evidence/e2e-*.png | Passed in Chromium and Firefox |
| FR5 | Search and filtering on a high-volume entity (Enrollment); fuzzed search input. | functional | `tests/api/test_contract.py::test_pagination_envelope`, `tests/fuzz/test_fuzz.py::test_search_endpoint_never_returns_500`, `tests/e2e/test_ui.py::test_learner_browse_and_logout` | pytest, Hypothesis, Playwright | evidence/api.xml, evidence/e2e.xml | Passed in Chromium and Firefox |
| FR6 | Audit log of sensitive actions recording who did what and when. | functional | `tests/unit/test_business_rules.py::test_br7_audit_written_for_writes_and_auth`, `tests/reliability/test_reliability.py::test_login_failure_is_logged_without_secret`, `tests/integration/test_api_flows.py::test_full_course_lifecycle` | pytest | evidence/unit.xml, evidence/api.xml | Passed |
| FR7 | At least five explicit, documented, testable business rules (BR1..BR8). | functional | `tests/unit/test_business_rules.py` (8 rule tests) | pytest | evidence/unit.xml | Passed - 9 unit tests |

## Quality requirements (ISO/IEC 25010)

| Requirement ID | Description | Type | Test(s) | Tool(s) | Evidence path | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | Functional suitability: all section 4 features implemented and accurate. | quality | full unit, integration, API, fuzz, smoke and E2E suites | pytest, Hypothesis, Playwright | evidence/unit.xml, evidence/api.xml, evidence/e2e.xml | Passed - 49 tests executed |
| Q2 | Performance efficiency: response time measured under load (target below 500 ms at 20 concurrent users). | quality | Locust, 20 users, 30 s, 940 requests, CSV + text output | Locust | evidence/performance.txt, evidence/perf_stats.csv, evidence/charts/performance_p95.png | Passed - aggregated p50 7 ms, p95 17 ms; login p50 76 ms, p95 97 ms |
| Q3 | Compatibility: runs on at least two browsers. | quality | 4 journeys x Chromium + Firefox | Playwright | evidence/e2e.xml | Passed - 8/8 browser tests |
| Q4 | Usability: validated user journeys and automated WCAG A/AA accessibility scan. | quality | Playwright journeys + axe-core scan of login and dashboard | Playwright, axe-core | evidence/e2e.xml, evidence/axe.json, evidence/e2e-*.png | Passed after fixing two color-contrast findings; 0 violations at final run |
| Q5 | Reliability: stable behavior on error, no data loss, transactions roll back, concurrent submits do not duplicate data. | quality | `tests/reliability/test_reliability.py` (3 scenarios) + `test_concurrency.py` | pytest | evidence/api.xml | Passed - 4 reliability/concurrency scenarios |
| Q6 | Security: robust authentication, RBAC, no known vulnerabilities across OWASP Top 10. | quality | Bandit SAST, pip-audit SCA, npm audit frontend SCA, OWASP ZAP DAST, negative RBAC tests | Bandit, pip-audit, npm audit, ZAP, pytest | evidence/bandit.txt, evidence/pip-audit.txt, evidence/npm-audit.txt, evidence/zap.html, evidence/zap.json, evidence/api.xml | Passed - 0 SAST issues, 0 Python CVEs, 0 npm vulnerabilities, 0 DAST failures (1 informational alert) |
| Q7 | Maintainability: layered code and measured test coverage (target at least 80%). | quality | coverage run + Bandit | pytest-cov, Bandit | evidence/coverage/index.html, evidence/coverage.xml, evidence/charts/coverage_by_module.png, evidence/bandit.txt | Passed - 88% coverage |
| Q8 | Portability: reproducible installation via container definition. | quality | Compose config validation plus live stack deployment and API smoke checks | Docker Compose | evidence/docker-compose-config.txt, evidence/docker-compose-up.txt, evidence/docker-stack-verification.txt | Passed - all three containers healthy; API and UI respond |

## Additional test layers beyond the specification

| Layer | Purpose | Tool | Test(s) | Evidence |
| --- | --- | --- | --- | --- |
| Property-based / fuzz | Adversarial inputs for schemas, hashing and search endpoint | Hypothesis | `tests/fuzz/test_fuzz.py` (6 tests, 300+ generated examples) | evidence/api.xml |
| Smoke | Post-deployment checks on demo accounts and core endpoints | pytest | `tests/smoke/test_smoke.py` (5 tests) | evidence/api.xml |
| Concurrency | Parallel double-submit cannot create duplicate enrollment | pytest + threads | `tests/reliability/test_concurrency.py` | evidence/api.xml |
| Accessibility | Automated WCAG A/AA violation scan | axe-core via Playwright | `tests/e2e/test_accessibility.py` | evidence/axe.json |
| Dashboard navigation simulation | Real-browser CDP tour of the three roles and their dashboards/windows | automation_engine.py + Playwright connect_over_cdp | `tests/e2e/test_dashboard_simulation.py` | evidence/dashboard_tour.json, evidence/dashboard_tour_*.png, Part II of both reports |
| Frontend SCA | Known vulnerabilities in frontend dependencies | npm audit | `npm audit` | evidence/npm-audit.txt |

## Evidence file index

| Path | Produced by | Content |
| --- | --- | --- |
| evidence/unit.xml | pytest | Business-rule test results |
| evidence/api.xml | pytest + httpx + Hypothesis | API, integration, reliability, fuzz and smoke results |
| evidence/e2e.xml | Playwright | Cross-browser and accessibility results |
| evidence/e2e-*.png | Playwright | Screenshots of verified journeys |
| evidence/tests.xml | pytest | Combined non-browser suite result |
| evidence/performance.txt, evidence/perf_*.csv | Locust | Load metrics and response-time percentiles |
| evidence/bandit.txt | Bandit | Static application security findings |
| evidence/pip-audit.txt | pip-audit | Python dependency CVE findings |
| evidence/npm-audit.txt | npm audit | Frontend dependency CVE findings |
| evidence/zap.html, evidence/zap.json | OWASP ZAP | Dynamic application security report |
| evidence/axe.json | axe-core | Accessibility scan result |
| evidence/dashboard_tour.json | CDP simulation | Browser, role windows, assertions, page errors |
| evidence/dashboard_tour_*.png | CDP simulation | One screenshot per role and window |
| evidence/coverage/index.html, evidence/coverage.xml | pytest-cov | Coverage reports |
| evidence/charts/*.png | matplotlib | Charts embedded in the PDF reports |
| evidence/docker-compose-config.txt | `docker compose config` | Resolved Compose configuration |
| evidence/docker-compose-up.txt, evidence/docker-stack-verification.txt | Docker Compose + HTTP checks | Live container deployment proof |

A requirement is considered demonstrated only when every listed evidence file
exists and contains output from a real execution of the named tool. Unavailable
tools are recorded as gaps in `docs/iso25010-conformance.md`.
