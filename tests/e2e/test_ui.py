"""End-to-end browser tests run against the live SPA + API.

Run with: python -m pytest tests/e2e -m e2e
Requires E2E_BASE_URL (default http://localhost:5173) and seeded backend.
"""
import os

import pytest
from playwright.sync_api import expect, sync_playwright

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:5173")
EVIDENCE_DIR = os.path.join(os.getcwd(), "evidence")
os.makedirs(EVIDENCE_DIR, exist_ok=True)


@pytest.fixture(scope="module")
def playwright_instance():
    with sync_playwright() as instance:
        yield instance


@pytest.fixture(params=["chromium", "firefox"])
def browser(playwright_instance, request):
    browser_type = getattr(playwright_instance, request.param)
    instance = browser_type.launch(headless=True)
    yield instance, request.param
    instance.close()


@pytest.fixture()
def page(browser):
    instance, name = browser
    context = instance.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.set_default_timeout(15000)
    yield page, name
    context.close()


def login(page, email, password):
    page.goto(BASE_URL)
    page.get_by_test_id("login-email").fill(email)
    page.get_by_test_id("login-password").fill(password)
    page.get_by_test_id("login-submit").click()
    page.wait_for_url("**/dashboard")


@pytest.mark.e2e
def test_learner_browse_and_logout(page):
    browser_page, name = page
    login(browser_page, "apprenant@eduflow.com", "apprenant123")
    browser_page.get_by_test_id("nav-courses").click()
    browser_page.get_by_test_id("courses-search").fill("ISO")
    browser_page.get_by_test_id("courses-apply").click()
    expect(browser_page.locator("[data-testid^='course-row-']").first).to_be_visible()
    browser_page.get_by_test_id("nav-enrollments").click()
    expect(browser_page.get_by_test_id("enrollments-filters")).to_be_visible()
    browser_page.screenshot(path=os.path.join(EVIDENCE_DIR, f"e2e-learner-{name}.png"), full_page=True)
    browser_page.get_by_test_id("logout-button").click()
    browser_page.wait_for_url("**/login")


@pytest.mark.e2e
def test_admin_rbac_navigation(page):
    browser_page, name = page
    login(browser_page, "admin@eduflow.com", "admin123")
    expect(browser_page.get_by_test_id("nav-audit")).to_be_visible()
    browser_page.get_by_test_id("nav-audit").click()
    expect(browser_page.get_by_test_id("audit-filters")).to_be_visible()
    browser_page.get_by_test_id("nav-users").click()
    expect(browser_page.get_by_test_id("user-create")).to_be_visible()
    browser_page.screenshot(path=os.path.join(EVIDENCE_DIR, f"e2e-admin-{name}.png"), full_page=True)


@pytest.mark.e2e
def test_learner_denied_admin_pages(page):
    browser_page, name = page
    login(browser_page, "apprenant@eduflow.com", "apprenant123")
    assert browser_page.get_by_test_id("nav-users").count() == 0
    browser_page.goto(f"{BASE_URL}/users")
    expect(browser_page.get_by_test_id("access-denied")).to_be_visible()
    browser_page.screenshot(path=os.path.join(EVIDENCE_DIR, f"e2e-rbac-{name}.png"), full_page=True)


@pytest.mark.e2e
def test_formateur_dashboard_metrics(page):
    browser_page, name = page
    login(browser_page, "formateur@eduflow.com", "form1234")
    browser_page.get_by_test_id("nav-dashboard").click()
    expect(browser_page.locator("[data-testid^='metric-card-']").first).to_be_visible()
    browser_page.screenshot(path=os.path.join(EVIDENCE_DIR, f"e2e-dashboard-{name}.png"), full_page=True)
