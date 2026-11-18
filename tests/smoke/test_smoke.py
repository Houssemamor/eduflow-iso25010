"""Post-deployment smoke checks: the smallest set of live paths that must work."""
import pytest


@pytest.mark.parametrize("role,key", [
    ("admin", "admin"),
    ("formateur", "formateur"),
    ("apprenant", "learner"),
])
def test_demo_account_login(client, role, key, tokens):
    response = client.get("/api/v1/auth/me", headers=tokens[key])
    assert response.status_code == 200
    assert response.json()["role"] == role


def test_core_pages_respond(client, tokens):
    for path in (
        "/api/v1/courses",
        "/api/v1/sessions",
        "/api/v1/enrollments",
        "/api/v1/dashboard",
    ):
        response = client.get(path, headers=tokens["learner"])
        assert response.status_code == 200, path


def test_health(client):
    assert client.get("/health").status_code == 200
