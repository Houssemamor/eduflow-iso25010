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

## Test commands

Commands are run from the repository root unless noted.

```sh
# Unit and API tests with coverage
pytest --cov=app --cov-report=html:evidence/coverage --junitxml=evidence/unit.xml tests

# Static application security testing
bandit -r app -f txt -o evidence/bandit.txt

# Dependency vulnerability scan
pip-audit -r requirements.txt -f text -o evidence/pip-audit.txt

# End-to-end tests (from the frontend directory)
cd frontend && npx playwright test

# Load test
locust -f tests/performance/locustfile.py --headless -u 20 -r 2 -t 60s

# Validate the container definition
docker compose config > evidence/docker-compose-config.txt
```

## Evidence location

Raw reports are written under `evidence/` (XML test reports, coverage HTML,
security scans, performance output, ZAP report, Docker Compose configuration).
The traceability matrix maps each requirement to the exact file that will hold
its evidence. These files are produced by executions of the commands above and
by the CI workflow in `.github/workflows/ci.yml`; this repository does not ship
pre-filled results.

## Generating the design reports

```sh
python tools/generate_reports.py
```

This writes `reports/Design_Report_EN.docx` and
`reports/Rapport_de_Conception_FR.docx` from the Markdown documentation, and
attempts a PDF conversion for each.
