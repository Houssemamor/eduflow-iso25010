"""Business-rule layer. All domain decisions are centralised and testable here."""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog, Course, Enrollment, Session, Tag, User, course_tags, utcnow
from app.security import hash_password, verify_password


class BusinessRuleError(Exception):
    """Domain violation carrying the HTTP status the API layer should return."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def write_audit(
    db: Session,
    actor_id: int | None,
    action: str,
    target_type: str,
    target_id: Any = None,
    detail: str = "",
) -> None:
    """Append-only audit record; called for every write and auth event."""
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=None if target_id is None else str(target_id),
            detail=detail,
        )
    )


# --- Users and authentication ------------------------------------------------

def list_users(db: Session, skip: int = 0, limit: int = 50) -> tuple[list[User], int]:
    total = db.scalar(select(func.count()).select_from(User)) or 0
    users = list(db.scalars(select(User).order_by(User.id).offset(skip).limit(limit)))
    return users, total


def create_user(db: Session, actor_id: int, data: Any) -> User:
    # BR1: email is unique case-insensitively.
    if db.scalar(select(User).where(func.lower(User.email) == data.email.lower())):
        raise BusinessRuleError("Email already registered", 409)
    user = User(
        email=data.email.lower(),
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.flush()
    write_audit(db, actor_id, "user.create", "user", user.id, f"role={user.role}")
    db.commit()
    return user


def update_user(db: Session, actor_id: int, user_id: int, data: Any) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise BusinessRuleError("User not found", 404)
    for field in ("full_name", "role", "is_active"):
        value = getattr(data, field)
        if value is not None:
            setattr(user, field, value)
    write_audit(db, actor_id, "user.update", "user", user_id)
    db.commit()
    return user


def delete_user(db: Session, actor_id: int, user_id: int) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise BusinessRuleError("User not found", 404)
    if db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.user_id == user_id)):
        raise BusinessRuleError("Cannot delete a user with enrollments", 409)
    db.delete(user)
    write_audit(db, actor_id, "user.delete", "user", user_id)
    db.commit()


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(func.lower(User.email) == email.lower()))
    if user is None or not verify_password(password, user.hashed_password) or not user.is_active:
        write_audit(db, None if user is None else user.id, "auth.login_failed", "user", None, email)
        db.commit()
        raise BusinessRuleError("Invalid credentials", 401)
    write_audit(db, user.id, "auth.login", "user", user.id)
    db.commit()
    return user


# --- Tags --------------------------------------------------------------------

def list_tags(db: Session) -> list[Tag]:
    return list(db.scalars(select(Tag).order_by(Tag.name)))


def create_tag(db: Session, actor_id: int, data: Any) -> Tag:
    if db.scalar(select(Tag).where(func.lower(Tag.name) == data.name.lower())):
        raise BusinessRuleError("Tag name already exists", 409)
    tag = Tag(name=data.name, color=data.color)
    db.add(tag)
    db.flush()
    write_audit(db, actor_id, "tag.create", "tag", tag.id)
    db.commit()
    return tag


def delete_tag(db: Session, actor_id: int, tag_id: int) -> None:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise BusinessRuleError("Tag not found", 404)
    db.delete(tag)
    write_audit(db, actor_id, "tag.delete", "tag", tag_id)
    db.commit()


# --- Courses -----------------------------------------------------------------

def get_course(db: Session, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise BusinessRuleError("Course not found", 404)
    return course


def list_courses(
    db: Session, q: str | None, status: str | None, tag_id: int | None,
    skip: int, limit: int
) -> tuple[list[Course], int]:
    stmt = select(Course)
    count_stmt = select(func.count()).select_from(Course)
    if q:
        stmt = stmt.where(Course.title.ilike(f"%{q}%"))
        count_stmt = count_stmt.where(Course.title.ilike(f"%{q}%"))
    if status:
        stmt = stmt.where(Course.status == status)
        count_stmt = count_stmt.where(Course.status == status)
    if tag_id is not None:
        stmt = stmt.join(course_tags, course_tags.c.course_id == Course.id).where(
            course_tags.c.tag_id == tag_id
        )
        count_stmt = count_stmt.join(course_tags, course_tags.c.course_id == Course.id).where(
            course_tags.c.tag_id == tag_id
        )
    total = db.scalar(count_stmt) or 0
    courses = list(db.scalars(stmt.order_by(Course.id).offset(skip).limit(limit)))
    return courses, total


def _set_course_tags(db: Session, course: Course, tag_ids: list[int]) -> None:
    tags = list(db.scalars(select(Tag).where(Tag.id.in_(tag_ids)))) if tag_ids else []
    if len(tags) != len(set(tag_ids)):
        raise BusinessRuleError("Unknown tag id", 422)
    course.tags = tags


def create_course(db: Session, actor: User, data: Any) -> Course:
    course = Course(
        title=data.title,
        description=data.description,
        capacity=data.capacity,
        status=data.status,
        owner_id=actor.id,
    )
    _set_course_tags(db, course, data.tag_ids)
    db.add(course)
    db.flush()
    write_audit(db, actor.id, "course.create", "course", course.id)
    db.commit()
    return course


def update_course(db: Session, actor: User, course_id: int, data: Any) -> Course:
    course = get_course(db, course_id)
    # BR4: staff may only edit their own courses unless they are admin.
    if actor.role != "admin" and course.owner_id != actor.id:
        raise BusinessRuleError("Not the course owner", 403)
    for field in ("title", "description", "capacity", "status"):
        value = getattr(data, field)
        if value is not None:
            setattr(course, field, value)
    if data.tag_ids is not None:
        _set_course_tags(db, course, data.tag_ids)
    write_audit(db, actor.id, "course.update", "course", course_id)
    db.commit()
    return course


def delete_course(db: Session, actor: User, course_id: int) -> None:
    course = get_course(db, course_id)
    if actor.role != "admin" and course.owner_id != actor.id:
        raise BusinessRuleError("Not the course owner", 403)
    # BR6: no deletion while validated enrollments exist.
    if db.scalar(
        select(func.count()).select_from(Enrollment).where(
            Enrollment.course_id == course_id, Enrollment.status == "validated"
        )
    ):
        raise BusinessRuleError("Cannot delete a course with validated enrollments", 409)
    db.delete(course)
    write_audit(db, actor.id, "course.delete", "course", course_id)
    db.commit()


# --- Sessions ----------------------------------------------------------------

def get_session(db: Session, session_id: int) -> Session:
    session = db.get(Session, session_id)
    if session is None:
        raise BusinessRuleError("Session not found", 404)
    return session


def list_sessions(
    db: Session, course_id: int | None, date_from: datetime | None, date_to: datetime | None
) -> list[Session]:
    stmt = select(Session)
    if course_id is not None:
        stmt = stmt.where(Session.course_id == course_id)
    if date_from is not None:
        stmt = stmt.where(Session.starts_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Session.ends_at <= date_to)
    return list(db.scalars(stmt.order_by(Session.starts_at)))


def create_session(db: Session, actor: User, data: Any) -> Session:
    course = get_course(db, data.course_id)
    if actor.role != "admin" and course.owner_id != actor.id:
        raise BusinessRuleError("Not the course owner", 403)
    if data.ends_at <= data.starts_at:
        raise BusinessRuleError("ends_at must be after starts_at", 422)
    session = Session(
        course_id=data.course_id, starts_at=data.starts_at, ends_at=data.ends_at,
        room=data.room, capacity=data.capacity,
    )
    db.add(session)
    db.flush()
    write_audit(db, actor.id, "session.create", "session", session.id)
    db.commit()
    return session


def update_session(db: Session, actor: User, session_id: int, data: Any) -> Session:
    session = get_session(db, session_id)
    if actor.role != "admin" and session.course.owner_id != actor.id:
        raise BusinessRuleError("Not the course owner", 403)
    starts = data.starts_at if data.starts_at is not None else session.starts_at
    ends = data.ends_at if data.ends_at is not None else session.ends_at
    if ends <= starts:
        raise BusinessRuleError("ends_at must be after starts_at", 422)
    for field in ("starts_at", "ends_at", "room", "capacity"):
        value = getattr(data, field)
        if value is not None:
            setattr(session, field, value)
    write_audit(db, actor.id, "session.update", "session", session_id)
    db.commit()
    return session


def delete_session(db: Session, actor: User, session_id: int) -> None:
    session = get_session(db, session_id)
    if actor.role != "admin" and session.course.owner_id != actor.id:
        raise BusinessRuleError("Not the course owner", 403)
    db.delete(session)
    write_audit(db, actor.id, "session.delete", "session", session_id)
    db.commit()


# --- Enrollments and workflow ------------------------------------------------

ALLOWED_TRANSITIONS = {
    "pending": {"validated", "cancelled"},
    "validated": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def list_enrollments(
    db: Session, actor: User, q: str | None, status: str | None, course_id: int | None,
    user_id: int | None, date_from: datetime | None, date_to: datetime | None,
    skip: int, limit: int
) -> tuple[list[Enrollment], int]:
    stmt = select(Enrollment).join(User).join(Course)
    count_stmt = (
        select(func.count()).select_from(Enrollment).join(User).join(Course)
    )
    if actor.role == "apprenant":
        stmt = stmt.where(Enrollment.user_id == actor.id)
        count_stmt = count_stmt.where(Enrollment.user_id == actor.id)
    elif actor.role == "formateur":
        stmt = stmt.where(Course.owner_id == actor.id)
        count_stmt = count_stmt.where(Course.owner_id == actor.id)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(User.full_name.ilike(pattern) | User.email.ilike(pattern) | Course.title.ilike(pattern))
        count_stmt = count_stmt.where(
            User.full_name.ilike(pattern) | User.email.ilike(pattern) | Course.title.ilike(pattern)
        )
    if status:
        stmt = stmt.where(Enrollment.status == status)
        count_stmt = count_stmt.where(Enrollment.status == status)
    if course_id is not None:
        stmt = stmt.where(Enrollment.course_id == course_id)
        count_stmt = count_stmt.where(Enrollment.course_id == course_id)
    if user_id is not None:
        stmt = stmt.where(Enrollment.user_id == user_id)
        count_stmt = count_stmt.where(Enrollment.user_id == user_id)
    if date_from is not None:
        stmt = stmt.where(Enrollment.created_at >= date_from)
        count_stmt = count_stmt.where(Enrollment.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Enrollment.created_at <= date_to)
        count_stmt = count_stmt.where(Enrollment.created_at <= date_to)
    total = db.scalar(count_stmt) or 0
    items = list(db.scalars(stmt.order_by(Enrollment.created_at.desc()).offset(skip).limit(limit)))
    return items, total


def create_enrollment(db: Session, actor: User, data: Any) -> Enrollment:
    course = get_course(db, data.course_id)
    if course.status != "published":
        raise BusinessRuleError("Course is not published", 409)
    # BR2: one enrollment per (user, course).
    if db.scalar(
        select(Enrollment).where(Enrollment.user_id == actor.id, Enrollment.course_id == course.id)
    ):
        raise BusinessRuleError("Already enrolled in this course", 409)
    session = None
    if data.session_id is not None:
        session = db.get(Session, data.session_id)
        if session is None or session.course_id != course.id:
            raise BusinessRuleError("Session does not belong to course", 422)
    enrollment = Enrollment(
        user_id=actor.id, course_id=course.id,
        session_id=None if session is None else session.id, status="pending",
    )
    db.add(enrollment)
    db.flush()
    write_audit(db, actor.id, "enrollment.create", "enrollment", enrollment.id)
    db.commit()
    return enrollment


def transition_enrollment(db: Session, actor: User, enrollment_id: int, new_status: str) -> Enrollment:
    enrollment = db.get(Enrollment, enrollment_id)
    if enrollment is None:
        raise BusinessRuleError("Enrollment not found", 404)
    course = enrollment.course
    # BR4: only staff may validate or complete; learners may only cancel their own.
    if new_status in {"validated", "completed"}:
        if actor.role == "apprenant":
            raise BusinessRuleError("Learners cannot validate enrollments", 403)
        if actor.role == "formateur" and course.owner_id != actor.id:
            raise BusinessRuleError("Not the course owner", 403)
    if new_status == "cancelled" and actor.role == "apprenant" and enrollment.user_id != actor.id:
        raise BusinessRuleError("Cannot cancel another learner's enrollment", 403)
    if new_status not in ALLOWED_TRANSITIONS[enrollment.status]:
        raise BusinessRuleError(
            f"Cannot move from {enrollment.status} to {new_status}", 409
        )
    if new_status == "validated":
        # BR3: seat availability is checked at validation time, not at creation.
        session = enrollment.session
        capacity = session.capacity if session else course.capacity
        used = db.scalar(
            select(func.count()).select_from(Enrollment).where(
                Enrollment.course_id == course.id, Enrollment.status == "validated"
            )
        ) or 0
        if used >= capacity:
            raise BusinessRuleError("No seats available", 409)
    if new_status == "completed":
        # BR5: completion is only possible after the session has ended.
        session = enrollment.session
        if session is not None and session.ends_at > utcnow():
            raise BusinessRuleError("Session has not ended", 409)
    enrollment.status = new_status
    enrollment.updated_at = utcnow()
    write_audit(
        db, actor.id, f"enrollment.{new_status}", "enrollment", enrollment_id,
        f"from={enrollment.status}",
    )
    db.commit()
    return enrollment


def delete_enrollment(db: Session, actor: User, enrollment_id: int) -> None:
    enrollment = db.get(Enrollment, enrollment_id)
    if enrollment is None:
        raise BusinessRuleError("Enrollment not found", 404)
    if actor.role == "apprenant" and enrollment.user_id != actor.id:
        raise BusinessRuleError("Cannot delete another learner's enrollment", 403)
    if enrollment.status == "validated":
        raise BusinessRuleError("Cancel a validated enrollment before deleting", 409)
    db.delete(enrollment)
    write_audit(db, actor.id, "enrollment.delete", "enrollment", enrollment_id)
    db.commit()


# --- Dashboard and audit -----------------------------------------------------

def get_dashboard(
    db: Session, course_id: int | None, status: str | None,
    date_from: datetime | None, date_to: datetime | None
) -> dict:
    stmt = select(Enrollment)
    if course_id is not None:
        stmt = stmt.where(Enrollment.course_id == course_id)
    if status:
        stmt = stmt.where(Enrollment.status == status)
    if date_from is not None:
        stmt = stmt.where(Enrollment.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Enrollment.created_at <= date_to)
    enrollments = list(db.scalars(stmt))
    counts = {name: 0 for name in ("pending", "validated", "completed", "cancelled")}
    for enrollment in enrollments:
        counts[enrollment.status] = counts.get(enrollment.status, 0) + 1
    capacity = db.scalar(select(func.coalesce(func.sum(Course.capacity), 0)).where(
        Course.status == "published"
    )) or 0
    by_course_rows = db.execute(
        select(Course.title, func.count(Enrollment.id))
        .join(Enrollment, Enrollment.course_id == Course.id, isouter=True)
        .group_by(Course.id, Course.title)
        .order_by(func.count(Enrollment.id).desc())
        .limit(10)
    ).all()
    recent = list(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(5)))
    return {
        "total_courses": db.scalar(select(func.count()).select_from(Course)) or 0,
        "total_enrollments": len(enrollments),
        "pending": counts["pending"],
        "validated": counts["validated"],
        "completed": counts["completed"],
        "cancelled": counts["cancelled"],
        "occupancy_rate": round(counts["validated"] / capacity, 4) if capacity else 0.0,
        "by_course": [{"title": title, "count": count} for title, count in by_course_rows],
        "recent_audit": [
            {"action": row.action, "target_type": row.target_type, "created_at": row.created_at.isoformat()}
            for row in recent
        ],
    }


def list_audit(
    db: Session, actor_id: int | None, action: str | None,
    date_from: datetime | None, date_to: datetime | None, skip: int, limit: int
) -> tuple[list[AuditLog], int]:
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)
    if actor_id is not None:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
        count_stmt = count_stmt.where(AuditLog.actor_id == actor_id)
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
        count_stmt = count_stmt.where(AuditLog.action.ilike(f"%{action}%"))
    if date_from is not None:
        stmt = stmt.where(AuditLog.created_at >= date_from)
        count_stmt = count_stmt.where(AuditLog.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(AuditLog.created_at <= date_to)
        count_stmt = count_stmt.where(AuditLog.created_at <= date_to)
    total = db.scalar(count_stmt) or 0
    items = list(db.scalars(stmt.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)))
    return items, total
