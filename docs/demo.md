# Soutenance demo checklist

This is the live demonstration required by the cahier des charges: the running
application plus **at least two test layers executed live**. The commands below
have been rehearsed; the recorded output is in `evidence/demo-check.txt`.

## 1. Start the application (about 1 minute)

```sh
docker compose up --build -d
docker compose ps
```

Expected: `db` healthy, `backend` and `frontend` running, ports 5432 / 8000 /
5173 published. Confirm `http://localhost:8000/health` returns
`{"status":"ok"}` and `http://localhost:5173` shows the EduFlow login page.

## 2. Show the application (about 2 minutes)

Log in with each profile and point out the differentiated rights:

| Profile | Email | Password | Show |
| --- | --- | --- | --- |
| admin | admin@eduflow.com | admin123 | Dashboard, Users, Audit log (admin-only navigation) |
| formateur | formateur@eduflow.com | form1234 | Dashboard, Courses, Enrollment validation buttons |
| apprenant | apprenant@eduflow.com | apprenant123 | Dashboard, course search, own enrollments, no Users/Audit links |

Optional: show the real-browser CDP simulation screenshots in Part II of either
PDF report (`evidence/dashboard_tour_*.png`).

## 3. Run two test layers live

**Layer 1 - API / integration (pytest + httpx):**

```sh
python -m pytest tests/api tests/integration -q
```

Expected: 16 passed. Point to `evidence/api.xml` for the committed report.

**Layer 2 - browser E2E (Playwright, Chromium + Firefox):**

```sh
python -m pytest tests/e2e/test_ui.py -m e2e -q
```

Expected: 8 passed (4 journeys in 2 browsers). Point to `evidence/e2e.xml`
and the `evidence/e2e-*.png` screenshots.

The whole rehearsal can be repeated with:

```sh
powershell -File tools/demo_check.ps1
```

## 4. Optional extras if time allows

- `python -m locust -f tests/performance/locustfile.py --headless -u 20 -r 5 -t 30s --host http://localhost:8000` - load chart with the 500 ms target.
- `python -m bandit -r app` and `python -m pip_audit -r requirements.txt` - the security scans already committed under `evidence/`.
- `python -m pytest tests/e2e/test_dashboard_simulation.py -m simulation -q` - real Edge driven through CDP.

## 5. Fallback

If the browser E2E layer cannot run on the presentation machine, use the unit
layer instead (`python -m pytest tests/unit -q`, expected 9 passed) and explain
that the E2E results and screenshots are committed as evidence with the exact
procedure in `docs/install.md`. No result is claimed without the corresponding
file in `evidence/`.
