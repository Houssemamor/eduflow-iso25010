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
| FR1 | Authentication and role management with three distinct profiles (admin, formateur, apprenant) and differentiated rights. | functional | `tests/integration/test_api_flows.py::test_login_and_me`, `::test_users_crud_and_rbac`, `tests/api/test_contract.py::test_unauthenticated_is_401`, `::test_invalid_token_is_401`, `::test_admin_endpoints_deny_learner` | pytest, httpx | evidence/api.xml | Passed - 19 API/integration tests |
| FR2 | At least four related business entities (User, Course, Session, Enrollment, plus Tag) with full CRUD and real 1-N and N-N relations. | functional | `tests/integration/test_api_flows.py::test_full_course_lifecycle`, `::test_users_crud_and_rbac`, `::test_tags_crud`, `::test_course_update_and_delete`, `::test_session_update_and_delete`, `tests/unit/test_business_rules.py::test_br2_unique_user_course_enrollment` | pytest, httpx | evidence/unit.xml, evidence/api.xml | Passed |
| FR3 | Status workflow (pending -> validated -> completed, cancellable) with enforced transition rules. | functional | `tests/unit/test_business_rules.py::test_workflow_allowed_transitions`, `::test_br3_capacity_checked_at_validation`, `::test_br5_completion_only_after_session_end`, `tests/reliability/test_reliability.py::test_failed_transition_leaves_state_unchanged` | pytest | evidence/unit.xml, evidence/api.xml | Passed |
| FR4 | Dashboard with aggregated indicators and filters. | functional | `tests/integration/test_api_flows.py::test_full_course_lifecycle`, `::test_dashboard_and_audit_filters`, `tests/e2e/test_ui.py::test_formateur_dashboard_metrics` | pytest, Playwright | evidence/api.xml, evidence/e2e.xml, evidence/e2e-*.png | Passed in Chromium and Firefox |
| FR5 | Search and filtering on a high-volume entity (Enrollment). | functional | `tests/api/test_contract.py::test_pagination_envelope`, `tests/e2e/test_ui.py::test_learner_browse_and_logout` (course search and enrollment filters) | pytest, httpx, Playwright | evidence/api.xml, evidence/e2e.xml | Passed in Chromium and Firefox |
| FR6 | Audit log of sensitive actions recording who did what and when. | functional | `tests/unit/test_business_rules.py::test_br7_audit_written_for_writes_and_auth`, `tests/reliability/test_reliability.py::test_login_failure_is_logged_without_secret`, `tests/integration/test_api_flows.py::test_full_course_lifecycle` | pytest | evidence/unit.xml, evidence/api.xml | Passed |
| FR7 | At least five explicit, documented, testable business rules (BR1..BR8). | functional | `tests/unit/test_business_rules.py` (8 rule tests) | pytest | evidence/unit.xml | Passed - 9 unit tests |

## Quality requirements (ISO/IEC 25010)

| Requirement ID | Description | Type | Test(s) | Tool(s) | Evidence path | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | Functional suitability: all section 4 features implemented and accurate. | quality | full unit, integration, API and E2E suites | pytest, Playwright | evidence/unit.xml, evidence/api.xml, evidence/e2e.xml | Passed - 36 tests executed |
| Q2 | Performance efficiency: response time measured under load (target below 500 ms at 20 concurrent users). | quality | Locust scenario with 20 users, 30 s, 911 requests | Locust | evidence/performance.txt | Passed for read endpoints (p50 6 ms, p95 190 ms). Login p50 490 ms, p95 810 ms - tail exceeds target due to bcrypt. |
| Q3 | Compatibility: runs on at least two browsers. | quality | 4 Playwright journeys x Chromium + Firefox | Playwright | evidence/e2e.xml | Passed - 8/8 browser tests |
| Q4 | Usability: validated user journeys and baseline accessibility. | quality | learner/admin/formateur journeys, labelled form controls, keyboard navigation | Playwright | evidence/e2e.xml, evidence/e2e-*.png | Passed for journeys; baseline a11y by semantic controls (no axe scan run). |
| Q5 | Reliability: stable behavior on error, no data loss, transactions roll back. | quality | `tests/reliability/test_reliability.py` (3 scenarios) | pytest | evidence/api.xml | Passed |
| Q6 | Security: robust authentication, RBAC, no known source vulnerabilities. | quality | Bandit SAST, dependency SCA, RBAC negative tests | Bandit, pip-audit, pytest | evidence/bandit.txt, evidence/pip-audit.txt, evidence/api.xml | Bandit: no issues. DAST (ZAP) executed only if container image is available; see conformance report. |
| Q7 | Maintainability: layered code and measured test coverage (target at least 80%). | quality | coverage run + Bandit clean result | pytest-cov, Bandit | evidence/coverage/index.html, evidence/coverage.xml, evidence/bandit.txt | Passed - 88% coverage |
| Q8 | Portability: reproducible installation via container definition. | quality | Compose config validation and documented clean install | Docker Compose | evidence/docker-compose-config.txt | Passed - config valid |

## Evidence file index

| Path | Produced by | Content |
| --- | --- | --- |
| evidence/unit.xml | pytest (`--junitxml`) | Business-rule test results |
| evidence/api.xml | pytest + httpx | API contract, integration and reliability results |
| evidence/e2e.xml | Playwright | Cross-browser end-to-end results |
| evidence/e2e-*.png | Playwright | Screenshots of verified journeys |
| evidence/tests.xml | pytest | Combined non-browser suite result |
| evidence/performance.txt | Locust | Load metrics and response-time percentiles |
| evidence/bandit.txt | Bandit | Static application security findings |
| evidence/pip-audit.txt | pip-audit | Dependency vulnerability findings |
| evidence/zap.html | OWASP ZAP | Dynamic application security report (when available) |
| evidence/coverage/index.html | pytest-cov | HTML coverage report |
| evidence/coverage.xml | pytest-cov | Cobertura coverage report |
| evidence/docker-compose-config.txt | `docker compose config` | Resolved Compose configuration |

A requirement is considered demonstrated only when every listed evidence file
exists and contains output from a real execution of the named tool. Unavailable
tools are recorded as gaps in `docs/iso25010-conformance.md`.
