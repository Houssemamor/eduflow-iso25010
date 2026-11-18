"""Simulated dashboard tour for the three roles using a real installed browser.

The harness detects Chrome/Edge via automation_engine, launches it with CDP,
then drives each role through its dashboard and role-specific pages. Screenshots
and a JSON trace are written to evidence/ as execution proof.
"""
import json
import os
import time
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

from automation_engine import (
    BROWSER_MISSING_MESSAGE,
    CDP_ENDPOINT,
    _resolve_browser_path,
    launch_cdp_browser,
    stop_browser,
)

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:5173")
EVIDENCE = Path(os.getcwd()) / "evidence"
PROFILE = Path(os.environ.get("TEMP", "/tmp")) / "eduflow-cdp-profile"

CREDENTIALS = {
    "admin": ("admin@eduflow.com", "admin123"),
    "formateur": ("formateur@eduflow.com", "form1234"),
    "apprenant": ("apprenant@eduflow.com", "apprenant123"),
}

ROLE_PLANS = {
    "admin": [
        ("/dashboard", "[data-testid^='metric-card-']", "aggregate metrics"),
        ("/users", "[data-testid='user-create']", "user management"),
        ("/audit", "[data-testid='audit-filters']", "audit log"),
    ],
    "formateur": [
        ("/dashboard", "[data-testid^='metric-card-']", "aggregate metrics"),
        ("/courses", "[data-testid='courses-filters']", "own course list"),
        ("/enrollments", "[data-testid='enrollments-filters']", "enrollment validation"),
    ],
    "apprenant": [
        ("/dashboard", "[data-testid^='metric-card-']", "aggregate metrics"),
        ("/courses", "[data-testid='courses-filters']", "course catalogue"),
        ("/enrollments", "[data-testid='enrollments-filters']", "own enrollments"),
    ],
}


@pytest.fixture(scope="module")
def cdp_browser():
    path = _resolve_browser_path()
    if not path:
        pytest.skip(BROWSER_MISSING_MESSAGE)
    process = launch_cdp_browser(path, str(PROFILE))
    yield path, process
    stop_browser(process)


def login(page, role):
    email, password = CREDENTIALS[role]
    page.goto(BASE_URL)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.get_by_test_id("login-email").fill(email)
    page.get_by_test_id("login-password").fill(password)
    page.get_by_test_id("login-submit").click()
    page.wait_for_url("**/dashboard")


@pytest.mark.e2e
@pytest.mark.simulation
def test_three_role_dashboard_tour(cdp_browser):
    browser_path, _ = cdp_browser
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "browser": os.path.basename(browser_path),
        "cdp_endpoint": CDP_ENDPOINT,
        "base_url": BASE_URL,
        "roles": {},
    }

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(CDP_ENDPOINT)
        context = browser.contexts[0]
        for role, plan in ROLE_PLANS.items():
            page = context.new_page()
            page.set_default_timeout(20000)
            page_errors = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            login(page, role)
            steps = []
            for index, (route, selector, description) in enumerate(plan):
                page.goto(f"{BASE_URL}{route}")
                expect(page.locator(selector).first).to_be_visible()
                screenshot = EVIDENCE / f"dashboard_tour_{role}_{index}_{route.strip('/')}.png"
                page.screenshot(path=str(screenshot), full_page=True)
                steps.append({
                    "route": route,
                    "assertion": description,
                    "selector": selector,
                    "screenshot": screenshot.name,
                })

            if role == "admin":
                expect(page.get_by_test_id("nav-users")).to_be_visible()
                expect(page.get_by_test_id("nav-audit")).to_be_visible()
            else:
                assert page.get_by_test_id("nav-users").count() == 0
                assert page.get_by_test_id("nav-audit").count() == 0

            report["roles"][role] = {
                "steps": steps,
                "admin_nav_visible": role == "admin",
                "page_errors": page_errors,
            }
            assert not page_errors, page_errors
            page.close()
        browser.close()

    output = EVIDENCE / "dashboard_tour.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    assert set(report["roles"]) == {"admin", "formateur", "apprenant"}
