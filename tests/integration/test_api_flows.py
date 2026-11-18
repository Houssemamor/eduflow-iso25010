"""Integration tests: API requests hitting the real (in-memory) database."""
from datetime import timedelta

from app.models import utcnow


def test_login_and_me(client, tokens):
    response = client.get("/api/v1/auth/me", headers=tokens["learner"])
    assert response.status_code == 200
    assert response.json()["role"] == "apprenant"


def test_full_course_lifecycle(client, tokens, db):
    from app.models import Course

    created = client.post(
        "/api/v1/courses",
        headers=tokens["formateur"],
        json={"title": "Integration course", "capacity": 3, "status": "published"},
    )
    assert created.status_code == 201, created.text
    course_id = created.json()["id"]

    listed = client.get("/api/v1/courses", headers=tokens["learner"])
    assert listed.status_code == 200
    assert any(item["id"] == course_id for item in listed.json()["items"])

    session = client.post(
        "/api/v1/sessions",
        headers=tokens["formateur"],
        json={
            "course_id": course_id,
            "starts_at": (utcnow() - timedelta(days=1)).isoformat(),
            "ends_at": (utcnow() + timedelta(days=1)).isoformat(),
            "room": "B1",
            "capacity": 3,
        },
    )
    assert session.status_code == 201, session.text

    enrollment = client.post(
        "/api/v1/enrollments",
        headers=tokens["learner"],
        json={"course_id": course_id, "session_id": session.json()["id"]},
    )
    assert enrollment.status_code == 201, enrollment.text
    enrollment_id = enrollment.json()["id"]

    validated = client.patch(
        f"/api/v1/enrollments/{enrollment_id}/status",
        headers=tokens["formateur"],
        json={"status": "validated"},
    )
    assert validated.status_code == 200, validated.text
    assert validated.json()["status"] == "validated"

    dashboard = client.get("/api/v1/dashboard", headers=tokens["admin"])
    assert dashboard.status_code == 200
    assert dashboard.json()["validated"] >= 1

    audit = client.get("/api/v1/audit", headers=tokens["admin"])
    assert audit.status_code == 200
    assert audit.json()["total"] >= 4

    response = client.delete(f"/api/v1/courses/{course_id}", headers=tokens["admin"])
    assert response.status_code == 409  # BR6 still protects the course


def test_users_crud_and_rbac(client, tokens):
    created = client.post(
        "/api/v1/users",
        headers=tokens["admin"],
        json={
            "email": "new@test.com", "password": "password123",
            "full_name": "New User", "role": "apprenant",
        },
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]
    assert client.patch(
        f"/api/v1/users/{user_id}", headers=tokens["admin"], json={"full_name": "Renamed"}
    ).status_code == 200
    assert client.get("/api/v1/users", headers=tokens["learner"]).status_code == 403
    assert client.delete(f"/api/v1/users/{user_id}", headers=tokens["admin"]).status_code == 204


def test_tags_crud(client, tokens):
    created = client.post("/api/v1/tags", headers=tokens["admin"], json={"name": "securite"})
    assert created.status_code == 201, created.text
    tag_id = created.json()["id"]
    assert any(tag["id"] == tag_id for tag in client.get(
        "/api/v1/tags", headers=tokens["learner"]
    ).json())
    assert client.delete(f"/api/v1/tags/{tag_id}", headers=tokens["admin"]).status_code == 204
    assert client.delete(f"/api/v1/tags/{tag_id}", headers=tokens["admin"]).status_code == 404


def test_course_update_and_delete(client, tokens):
    created = client.post(
        "/api/v1/courses", headers=tokens["formateur"],
        json={"title": "Draft course", "description": "init", "capacity": 4},
    )
    assert created.status_code == 201
    course_id = created.json()["id"]
    updated = client.patch(
        f"/api/v1/courses/{course_id}", headers=tokens["formateur"],
        json={"title": "Updated course", "capacity": 8, "status": "published"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated course"
    assert client.delete(
        f"/api/v1/courses/{course_id}", headers=tokens["formateur"]
    ).status_code == 204


def test_session_update_and_delete(client, tokens):
    course = client.post(
        "/api/v1/courses", headers=tokens["formateur"],
        json={"title": "Session course", "status": "published"},
    ).json()
    session = client.post(
        "/api/v1/sessions", headers=tokens["formateur"],
        json={
            "course_id": course["id"],
            "starts_at": (utcnow() - timedelta(days=1)).isoformat(),
            "ends_at": (utcnow() + timedelta(days=1)).isoformat(),
            "room": "C1", "capacity": 5,
        },
    )
    assert session.status_code == 201
    session_id = session.json()["id"]
    assert client.get(
        f"/api/v1/sessions?course_id={course['id']}", headers=tokens["learner"]
    ).status_code == 200
    patched = client.patch(
        f"/api/v1/sessions/{session_id}", headers=tokens["formateur"],
        json={"room": "C2", "capacity": 6},
    )
    assert patched.status_code == 200
    assert patched.json()["room"] == "C2"
    assert client.delete(
        f"/api/v1/sessions/{session_id}", headers=tokens["formateur"]
    ).status_code == 204


def test_enrollment_cancel_and_delete(client, tokens):
    course = client.post(
        "/api/v1/courses", headers=tokens["formateur"],
        json={"title": "Cancel course", "status": "published"},
    ).json()
    enrollment = client.post(
        "/api/v1/enrollments", headers=tokens["learner"],
        json={"course_id": course["id"]},
    )
    assert enrollment.status_code == 201
    enrollment_id = enrollment.json()["id"]
    assert client.patch(
        f"/api/v1/enrollments/{enrollment_id}/status", headers=tokens["learner"],
        json={"status": "cancelled"},
    ).status_code == 200
    assert client.delete(
        f"/api/v1/enrollments/{enrollment_id}", headers=tokens["learner"]
    ).status_code == 204


def test_dashboard_and_audit_filters(client, tokens):
    response = client.get(
        "/api/v1/dashboard?status=pending&date_from=2020-01-01T00:00:00",
        headers=tokens["admin"],
    )
    assert response.status_code == 200
    assert response.json()["total_enrollments"] >= 0
    audit = client.get("/api/v1/audit?action=login&limit=5", headers=tokens["admin"])
    assert audit.status_code == 200
    assert audit.json()["limit"] == 5
