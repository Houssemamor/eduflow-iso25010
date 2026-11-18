"""Property-based and fuzz tests (Hypothesis) for boundary validation.

These complement example-based tests by generating adversarial inputs and
asserting that the API never returns 500 and that schemas never crash.
"""
import string

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.schemas import CourseCreate, LoginRequest, UserCreate
from app.security import create_access_token, decode_token, hash_password, verify_password


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=60)
@given(
    email=st.text(min_size=1, max_size=80),
    password=st.text(min_size=1, max_size=90),
)
def test_login_schema_never_crashes(email, password):
    try:
        LoginRequest(email=email, password=password)
    except ValidationError:
        pass


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=60)
@given(
    title=st.text(min_size=0, max_size=300),
    capacity=st.integers(min_value=-5, max_value=5000),
    status=st.text(min_size=0, max_size=20),
    tag_ids=st.lists(st.integers(min_value=-3, max_value=10), max_size=6),
)
def test_course_schema_never_crashes(title, capacity, status, tag_ids):
    try:
        CourseCreate(title=title, capacity=capacity, status=status, tag_ids=tag_ids)
    except ValidationError:
        pass


@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
@given(password=st.text(alphabet=string.ascii_letters + string.digits, min_size=8, max_size=72))
def test_password_hash_round_trip(password):
    assert verify_password(password, hash_password(password)) is True
    assert verify_password(password + "x", hash_password(password)) is False


@settings(max_examples=50)
@given(token=st.text(min_size=0, max_size=120))
def test_arbitrary_token_is_rejected(token):
    with pytest.raises(Exception):
        decode_token(token)


@settings(
    max_examples=40,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
@given(term=st.text(min_size=0, max_size=60, alphabet=string.ascii_letters + "%_'\"-"))
def test_search_endpoint_never_returns_500(client, tokens, term):
    response = client.get(
        "/api/v1/courses", headers=tokens["admin"], params={"q": term}
    )
    assert response.status_code == 200
    assert isinstance(response.json()["items"], list)


def test_token_subject_round_trip():
    token = create_access_token("123", "admin")
    payload = decode_token(token)
    assert payload["sub"] == "123"
    assert payload["role"] == "admin"
