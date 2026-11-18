"""Automated accessibility scan with axe-core on the live SPA."""
import json
import os

import pytest
from playwright.sync_api import expect, sync_playwright

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:5173")
EVIDENCE_DIR = os.path.join(os.getcwd(), "evidence")
os.makedirs(EVIDENCE_DIR, exist_ok=True)
AXE_PATH = os.path.join(os.path.dirname(__file__), "axe.min.js")


@pytest.fixture(scope="module")
def a11y_browser():
    with sync_playwright() as instance:
        instance.chromium.launch(headless=True)
        browser = instance.chromium.launch(headless=True)
        yield browser, instance
        browser.close()


@pytest.fixture()
def a11y_page(a11y_browser):
    browser, _ = a11y_browser
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    target = context.new_page()
    target.set_default_timeout(15000)
    yield target
    context.close()


def scan(page):
    page.add_script_tag(path=AXE_PATH)
    return page.evaluate(
        "async () => await axe.run(document, { runOnly: ['wcag2a', 'wcag2aa'] })"
    )


@pytest.mark.e2e
@pytest.mark.accessibility
def test_axe_scan_login_and_dashboard(a11y_page):
    page = a11y_page
    page.goto(BASE_URL)
    expect(page.get_by_test_id("login-submit")).to_be_visible()
    login_result = scan(page)
    assert len(login_result["violations"]) == 0, [
        (v["id"], v["impact"]) for v in login_result["violations"]
    ]

    page.get_by_test_id("login-email").fill("admin@eduflow.com")
    page.get_by_test_id("login-password").fill("admin123")
    page.get_by_test_id("login-submit").click()
    page.wait_for_url("**/dashboard")
    expect(page.get_by_test_id("nav-dashboard")).to_be_visible()
    dashboard_result = scan(page)

    report = {
        "login_violations": login_result["violations"],
        "dashboard_violations": dashboard_result["violations"],
        "login_passes": len(login_result["passes"]),
        "dashboard_passes": len(dashboard_result["passes"]),
    }
    with open(os.path.join(EVIDENCE_DIR, "axe.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    assert len(dashboard_result["violations"]) == 0, [
        (v["id"], v["impact"]) for v in dashboard_result["violations"]
    ]
