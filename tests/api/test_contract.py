"""API contract tests: status codes, envelopes, validation and auth failures."""
import pytest


def test_unauthenticated_is_401(client):
    assert client.get("/api/v1/courses").status_code == 401


def test_invalid_token_is_401(client):
    response = client.get(
        "/api/v1/courses", headers={"Authorization": "Bearer not.a.jwt"}
    )
    assert response.status_code == 401
    assert "detail" in response.json()


def test_pagination_envelope(client, tokens):
    response = client.get("/api/v1/enrollments", headers=tokens["learner"])
    assert response.status_code == 200
    body = response.json()
    assert set(["items", "total", "skip", "limit"]).issubset(body)
    assert isinstance(body["items"], list)


def test_validation_error_shape(client, tokens):
    response = client.post(
        "/api/v1/courses", headers=tokens["formateur"], json={"title": "ab"}
    )
    assert response.status_code == 422
    assert "detail" in response.json()


def test_not_found_shape(client, tokens):
    response = client.get("/api/v1/courses/999999", headers=tokens["admin"])
    assert response.status_code == 404
    assert response.json()["detail"] == "Course not found"


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("path", [
    "/api/v1/users", "/api/v1/audit",
])
def test_admin_endpoints_deny_learner(client, tokens, path):
    assert client.get(path, headers=tokens["learner"]).status_code == 403
