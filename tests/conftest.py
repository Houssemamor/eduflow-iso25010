"""Shared fixtures. Environment is set before any app module is imported."""
import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-only-secret-with-at-least-32-bytes"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
Base.metadata.create_all(bind=test_engine)


def make_user(db, email="user@test.com", role="apprenant", password="password123"):
    user = User(
        email=email, full_name="Test User", role=role,
        hashed_password=hash_password(password),
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def tokens(client, db):
    """Create the three demo profiles and return their bearer headers."""
    for email, role, password in (
        ("admin@test.com", "admin", "admin1234"),
        ("formateur@test.com", "formateur", "form1234"),
        ("apprenant@test.com", "apprenant", "learn1234"),
    ):
        make_user(db, email, role, password)
    headers = {}
    for key, email, password in (
        ("admin", "admin@test.com", "admin1234"),
        ("formateur", "formateur@test.com", "form1234"),
        ("learner", "apprenant@test.com", "learn1234"),
    ):
        response = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200, response.text
        headers[key] = {"Authorization": f"Bearer {response.json()['access_token']}"}
    return headers
