# EduFlow Installation and Run Guide

This guide lets a third party reproduce the EduFlow environment from scratch.
All commands are run from the repository root unless a directory is stated.

## 1. Prerequisites

- Docker Engine 24 or newer and Docker Compose v2 (`docker compose version`).
- Python 3.14 with pip (for manual backend setup and local test runs).
- Node.js 20 with npm (for manual frontend setup and Playwright).
- Git (to obtain the source).

Verify Docker before continuing:

```sh
docker --version
docker compose version
```

## 2. Quick start with Docker Compose

This is the recommended path. It builds the backend and frontend images and
starts PostgreSQL, the API and the SPA.

```sh
git clone <repository-url> eduflow
cd eduflow
docker compose up --build
```

First startup initializes the database schema and demo accounts. Services:

| Service | URL / port |
| --- | --- |
| Backend API | http://localhost:8000 (interactive docs at /docs) |
| Frontend SPA | http://localhost:5173 |
| PostgreSQL | localhost:5432 |

Stop and remove containers and volumes:

```sh
docker compose down -v
```

Rebuild after changing dependencies:

```sh
docker compose up --build --force-recreate
```

## 3. Manual backend setup

```sh
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
# source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

Configure the environment (never commit real secrets):

```sh
# PowerShell example
$env:DATABASE_URL="postgresql://eduflow:eduflow_dev_password@localhost:5432/eduflow"
$env:JWT_SECRET="replace-with-a-long-random-secret"
$env:ACCESS_TOKEN_EXPIRE_MINUTES="60"
```

Start a local database if Docker is not used for it:

```sh
docker compose up -d db
```

Create the schema and seed demo data, then start the API:

```sh
python seed.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`seed.py` is idempotent: it creates the tables and inserts the demo accounts and
sample content only when they are absent.

## 4. Manual frontend setup

```sh
cd frontend
npm ci
npm run dev -- --host 0.0.0.0
```

The SPA runs on http://localhost:5173 and expects the API at
http://localhost:8000. For a production build:

```sh
npm run build
```

## 5. Demo accounts

| Role | Email | Password |
| --- | --- | --- |
| admin | admin@eduflow.com | admin123 |
| formateur | formateur@eduflow.com | form1234 |
| apprenant | apprenant@eduflow.com | apprenant123 |

These accounts are seeded for demonstration only. The email domain is defined by
`seed.py`; if that file uses a different domain, use the credentials it actually
creates. Change or remove demo accounts before any non-local deployment.

## 6. Running the tests

```sh
# Unit and API tests with XML + HTML coverage evidence
pytest --cov=app --cov-report=html:evidence/coverage \
  --cov-report=xml:evidence/coverage.xml \
  --junitxml=evidence/unit.xml tests

# Static application security testing (SAST)
bandit -r app -f txt -o evidence/bandit.txt

# Dependency vulnerability scan (SCA)
pip-audit -r requirements.txt -f text -o evidence/pip-audit.txt

# End-to-end tests in Chromium and Firefox
cd frontend
npx playwright install chromium firefox
npx playwright test --reporter=junit --output-file=../evidence/e2e.xml

# Load test (stack must be running)
cd ..
locust -f tests/performance/locustfile.py --headless -u 20 -r 2 -t 60s \
  > evidence/performance.txt

# Dynamic application security scan (stack must be running, ZAP installed)
zap-baseline.py -t http://localhost:8000 -r zap.html
# move the generated zap.html to evidence/zap.html

# Portability validation
docker compose config > evidence/docker-compose-config.txt
```

Create the `evidence/` directory first if it does not exist (`mkdir -p evidence`
on Linux/macOS, `New-Item -ItemType Directory evidence` on Windows PowerShell).

The browser, load and DAST tools are not part of the Python test dependencies.
Install `@playwright/test` in `frontend/` and a Locust script at
`tests/performance/locustfile.py` before running those layers; if a tool cannot
be made available, record it as a gap in `docs/iso25010-conformance.md` instead
of reporting a fabricated result.

## 7. Generating the design reports

```sh
python tools/generate_reports.py
```

Outputs are written to `reports/`: `Design_Report_EN.docx`,
`Rapport_de_Conception_FR.docx`, and PDF versions when a converter or the
built-in fallback succeeds.

## 8. Troubleshooting

- **Port already in use:** stop the conflicting service or change the mapped
  ports in `docker-compose.yml`.
- **Database connection refused:** confirm the `db` service is healthy and that
  `DATABASE_URL` matches the credentials in the Compose file.
- **frontend cannot reach API:** check CORS settings and that port 8000 is
  exposed; use the documented URLs rather than `localhost` inside containers.
- **Playwright browsers missing:** run `npx playwright install` with network
  access once, then tests run offline.
