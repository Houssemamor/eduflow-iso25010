"""REST API routers. Thin layer: validation, dependency checks, delegation."""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app import services
from app.db import get_db
from app.models import User
from app.schemas import (
    AuditOut, CourseCreate, CourseOut, CourseUpdate, DashboardOut, EnrollmentCreate,
    EnrollmentOut, EnrollmentStatusUpdate, LoginRequest, Paginated, SessionCreate,
    SessionOut, SessionUpdate, TagCreate, TagOut, TokenOut, UserCreate, UserOut, UserUpdate,
)
from app.security import (
    create_access_token, get_current_user, require_admin, require_staff,
)

router = APIRouter(prefix="/api/v1")
AUTH_SCHEME = "bearer"  # OAuth2 scheme name; not a credential.


@router.post("/auth/login", response_model=TokenOut)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = services.authenticate(db, data.email, data.password)
    return {
        "access_token": create_access_token(str(user.id), user.role),
        "token_type": AUTH_SCHEME,
        "user": user,
    }


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/users", response_model=Paginated[UserOut])
def users_list(
    skip: int = 0, limit: int = Query(50, le=200),
    db: Session = Depends(get_db), _=Depends(require_admin),
):
    items, total = services.list_users(db, skip, limit)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def users_create(
    data: UserCreate, db: Session = Depends(get_db), actor=Depends(require_admin),
):
    return services.create_user(db, actor.id, data)


@router.get("/users/{user_id}", response_model=UserOut)
def users_get(user_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    user = db.get(User, user_id)
    if user is None:
        raise services.BusinessRuleError("User not found", 404)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def users_update(
    user_id: int, data: UserUpdate,
    db: Session = Depends(get_db), actor=Depends(require_admin),
):
    return services.update_user(db, actor.id, user_id, data)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def users_delete(user_id: int, db: Session = Depends(get_db), actor=Depends(require_admin)):
    services.delete_user(db, actor.id, user_id)


@router.get("/tags", response_model=list[TagOut])
def tags_list(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return services.list_tags(db)


@router.post("/tags", response_model=TagOut, status_code=status.HTTP_201_CREATED)
def tags_create(data: TagCreate, db: Session = Depends(get_db), actor=Depends(require_admin)):
    return services.create_tag(db, actor.id, data)


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def tags_delete(tag_id: int, db: Session = Depends(get_db), actor=Depends(require_admin)):
    services.delete_tag(db, actor.id, tag_id)


@router.get("/courses", response_model=Paginated[CourseOut])
def courses_list(
    q: str | None = None, status_filter: str | None = Query(None, alias="status"),
    tag_id: int | None = None, skip: int = 0, limit: int = Query(50, le=200),
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    items, total = services.list_courses(db, q, status_filter, tag_id, skip, limit)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/courses", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def courses_create(data: CourseCreate, db: Session = Depends(get_db), actor=Depends(require_staff)):
    return services.create_course(db, actor, data)


@router.get("/courses/{course_id}", response_model=CourseOut)
def courses_get(course_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return services.get_course(db, course_id)


@router.patch("/courses/{course_id}", response_model=CourseOut)
def courses_update(
    course_id: int, data: CourseUpdate,
    db: Session = Depends(get_db), actor=Depends(require_staff),
):
    return services.update_course(db, actor, course_id, data)


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def courses_delete(course_id: int, db: Session = Depends(get_db), actor=Depends(require_staff)):
    services.delete_course(db, actor, course_id)


@router.get("/sessions", response_model=list[SessionOut])
def sessions_list(
    course_id: int | None = None, date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    return services.list_sessions(db, course_id, date_from, date_to)


@router.post("/sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def sessions_create(data: SessionCreate, db: Session = Depends(get_db), actor=Depends(require_staff)):
    return services.create_session(db, actor, data)


@router.patch("/sessions/{session_id}", response_model=SessionOut)
def sessions_update(
    session_id: int, data: SessionUpdate,
    db: Session = Depends(get_db), actor=Depends(require_staff),
):
    return services.update_session(db, actor, session_id, data)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def sessions_delete(session_id: int, db: Session = Depends(get_db), actor=Depends(require_staff)):
    services.delete_session(db, actor, session_id)


@router.get("/enrollments", response_model=Paginated[EnrollmentOut])
def enrollments_list(
    q: str | None = None, status_filter: str | None = Query(None, alias="status"),
    course_id: int | None = None, user_id: int | None = None,
    date_from: datetime | None = None, date_to: datetime | None = None,
    skip: int = 0, limit: int = Query(50, le=200),
    db: Session = Depends(get_db), actor=Depends(get_current_user),
):
    items, total = services.list_enrollments(
        db, actor, q, status_filter, course_id, user_id, date_from, date_to, skip, limit
    )
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/enrollments", response_model=EnrollmentOut, status_code=status.HTTP_201_CREATED)
def enrollments_create(
    data: EnrollmentCreate, db: Session = Depends(get_db), actor=Depends(get_current_user),
):
    return services.create_enrollment(db, actor, data)


@router.patch("/enrollments/{enrollment_id}/status", response_model=EnrollmentOut)
def enrollments_transition(
    enrollment_id: int, data: EnrollmentStatusUpdate,
    db: Session = Depends(get_db), actor=Depends(get_current_user),
):
    return services.transition_enrollment(db, actor, enrollment_id, data.status)


@router.delete("/enrollments/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
def enrollments_delete(
    enrollment_id: int, db: Session = Depends(get_db), actor=Depends(get_current_user),
):
    services.delete_enrollment(db, actor, enrollment_id)


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(
    course_id: int | None = None, status_filter: str | None = Query(None, alias="status"),
    date_from: datetime | None = None, date_to: datetime | None = None,
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    return services.get_dashboard(db, course_id, status_filter, date_from, date_to)


@router.get("/audit", response_model=Paginated[AuditOut])
def audit_list(
    actor_id: int | None = None, action: str | None = None,
    date_from: datetime | None = None, date_to: datetime | None = None,
    skip: int = 0, limit: int = Query(50, le=200),
    db: Session = Depends(get_db), _=Depends(require_admin),
):
    items, total = services.list_audit(db, actor_id, action, date_from, date_to, skip, limit)
    return {"items": items, "total": total, "skip": skip, "limit": limit}
