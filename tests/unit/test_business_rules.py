"""Isolated business-rule tests (BR1..BR8)."""
from datetime import timedelta

import jwt
import pytest
from pydantic import ValidationError

from app import services
from app.config import settings
from app.models import AuditLog, Course, Enrollment, Session
from app.schemas import CourseCreate, EnrollmentCreate, LoginRequest, SessionCreate, UserCreate
from app.security import create_access_token, decode_token
from tests.conftest import make_user


def test_br1_unique_email_case_insensitive(db):
    admin = make_user(db, "admin@test.com", "admin")
    data = UserCreate(email="Duplicate@Test.com", password="password123", full_name="Dup User")
    assert services.create_user(db, admin.id, data).id
    with pytest.raises(services.BusinessRuleError) as exc:
        services.create_user(db, admin.id, data)
    assert exc.value.status_code == 409


def test_br2_unique_user_course_enrollment(db):
    learner = make_user(db, role="apprenant")
    course = Course(title="C", owner_id=learner.id, status="published", capacity=5)
    db.add(course)
    db.commit()
    data = EnrollmentCreate(course_id=course.id)
    assert services.create_enrollment(db, learner, data)
    with pytest.raises(services.BusinessRuleError):
        services.create_enrollment(db, learner, data)


def test_br3_capacity_checked_at_validation(db):
    learner = make_user(db, role="apprenant")
    course = Course(title="C", owner_id=learner.id, status="published", capacity=1)
    db.add(course)
    db.commit()
    first = services.create_enrollment(db, learner, EnrollmentCreate(course_id=course.id))
    staff = make_user(db, "staff@test.com", "admin")
    services.transition_enrollment(db, staff, first.id, "validated")
    other = make_user(db, "other@test.com", "apprenant")
    second = services.create_enrollment(db, other, EnrollmentCreate(course_id=course.id))
    with pytest.raises(services.BusinessRuleError) as exc:
        services.transition_enrollment(db, staff, second.id, "validated")
    assert "seats" in exc.value.message.lower()


def test_br4_ownership_and_role_enforced(db):
    owner = make_user(db, "owner@test.com", "formateur")
    other = make_user(db, "other@test.com", "formateur")
    course = services.create_course(
        db, owner, CourseCreate(title="Owned course", status="published")
    )
    with pytest.raises(services.BusinessRuleError) as exc:
        services.update_course(db, other, course.id, CourseCreate(title="Hijacked course"))
    assert exc.value.status_code == 403
    learner = make_user(db, "learner@test.com", "apprenant")
    enrollment = services.create_enrollment(db, learner, EnrollmentCreate(course_id=course.id, session_id=None))
    with pytest.raises(services.BusinessRuleError):
        services.transition_enrollment(db, learner, enrollment.id, "validated")


def test_br5_completion_only_after_session_end(db):
    staff = make_user(db, role="admin")
    learner = make_user(db, "l@test.com", "apprenant")
    course = Course(title="C", owner_id=staff.id, status="published", capacity=5)
    db.add(course)
    db.flush()
    from app.models import utcnow
    session = Session(
        course_id=course.id, starts_at=utcnow() - timedelta(days=2),
        ends_at=utcnow() + timedelta(days=2), room="A", capacity=5,
    )
    db.add(session)
    db.commit()
    enrollment = services.create_enrollment(
        db, learner, EnrollmentCreate(course_id=course.id, session_id=session.id)
    )
    services.transition_enrollment(db, staff, enrollment.id, "validated")
    with pytest.raises(services.BusinessRuleError):
        services.transition_enrollment(db, staff, enrollment.id, "completed")
    # Past sessions allow completion.
    session.ends_at = utcnow() - timedelta(days=1)
    db.commit()
    assert services.transition_enrollment(db, staff, enrollment.id, "completed").status == "completed"


def test_br6_no_course_delete_with_validated_enrollment(db):
    staff = make_user(db, role="admin")
    learner = make_user(db, "l@test.com", "apprenant")
    course = Course(title="C", owner_id=staff.id, status="published", capacity=5)
    db.add(course)
    db.commit()
    enrollment = services.create_enrollment(db, learner, EnrollmentCreate(course_id=course.id))
    services.transition_enrollment(db, staff, enrollment.id, "validated")
    with pytest.raises(services.BusinessRuleError):
        services.delete_course(db, staff, course.id)


def test_br7_audit_written_for_writes_and_auth(db):
    admin = make_user(db, role="admin")
    data = UserCreate(email="audited@test.com", password="password123", full_name="Audited")
    created = services.create_user(db, admin.id, data)
    actions = [row.action for row in db.query(AuditLog).all()]
    assert "user.create" in actions
    services.authenticate(db, data.email, data.password)
    assert "auth.login" in [row.action for row in db.query(AuditLog).all()]
    with pytest.raises(services.BusinessRuleError):
        services.authenticate(db, data.email, "wrongpassword")
    assert "auth.login_failed" in [row.action for row in db.query(AuditLog).all()]


def test_br8_password_and_token_strength(db):
    with pytest.raises(ValidationError):
        LoginRequest(email="a@b.com", password="short")
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", password="password123", full_name="A", role="superuser")
    token = create_access_token("1", "admin")
    assert decode_token(token)["sub"] == "1"
    with pytest.raises(Exception):
        decode_token(token + "tampered")


def test_workflow_allowed_transitions(db):
    staff = make_user(db, role="admin")
    learner = make_user(db, "l@test.com", "apprenant")
    course = Course(title="C", owner_id=staff.id, status="published", capacity=5)
    db.add(course)
    db.commit()
    enrollment = services.create_enrollment(db, learner, EnrollmentCreate(course_id=course.id))
    with pytest.raises(services.BusinessRuleError):
        services.transition_enrollment(db, staff, enrollment.id, "completed")
    services.transition_enrollment(db, staff, enrollment.id, "cancelled")
    assert enrollment.status == "cancelled"
