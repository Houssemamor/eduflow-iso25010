"""Reliability tests: no corruption on failure, duplicate or retry."""
from datetime import timedelta

from app.models import Course, Enrollment, Session, AuditLog, utcnow
from app.schemas import EnrollmentCreate
from app import services
from tests.conftest import make_user


def test_duplicate_enrollment_does_not_create_row(db):
    staff = make_user(db, role="admin")
    learner = make_user(db, "l@test.com", "apprenant")
    course = Course(title="C", owner_id=staff.id, status="published", capacity=5)
    db.add(course)
    db.commit()
    data = EnrollmentCreate(course_id=course.id)
    services.create_enrollment(db, learner, data)
    try:
        services.create_enrollment(db, learner, data)
    except services.BusinessRuleError:
        pass
    assert db.query(Enrollment).count() == 1


def test_failed_transition_leaves_state_unchanged(db):
    staff = make_user(db, role="admin")
    learner = make_user(db, "l@test.com", "apprenant")
    course = Course(title="C", owner_id=staff.id, status="published", capacity=5)
    db.add(course)
    db.flush()
    session = Session(
        course_id=course.id, starts_at=utcnow() - timedelta(days=1),
        ends_at=utcnow() + timedelta(days=5), capacity=5,
    )
    db.add(session)
    db.commit()
    enrollment = services.create_enrollment(
        db, learner,
        EnrollmentCreate(course_id=course.id, session_id=session.id),
    )
    try:
        services.transition_enrollment(db, staff, enrollment.id, "completed")
    except services.BusinessRuleError:
        pass
    db.refresh(enrollment)
    assert enrollment.status == "pending"
    assert db.query(AuditLog).filter(AuditLog.action.like("enrollment.completed%")).count() == 0


def test_login_failure_is_logged_without_secret(db):
    user = make_user(db, "l@test.com", "apprenant", "password123")
    try:
        services.authenticate(db, user.email, "totally-wrong-password")
    except services.BusinessRuleError:
        pass
    entry = db.query(AuditLog).filter(AuditLog.action == "auth.login_failed").first()
    assert entry is not None
    assert "totally-wrong-password" not in (entry.detail or "")
