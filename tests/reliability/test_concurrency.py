"""Concurrent double-submit must not create duplicate enrollments."""
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app import services
from app.models import Base, Course, Enrollment
from app.schemas import EnrollmentCreate


def test_parallel_double_enrollment_is_unique(tmp_path):
    db_path = tmp_path / "concurrency.db"
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    setup = factory()
    from app.models import User
    from app.security import hash_password
    learner = User(
        email="race@test.com", full_name="Race User", role="apprenant",
        hashed_password=hash_password("password123"),
    )
    course = Course(title="Race course", owner_id=1, status="published", capacity=10)
    setup.add_all([learner, course])
    setup.commit()
    user_id, course_id = learner.id, course.id
    setup.close()

    def enroll(_):
        session = factory()
        try:
            user = session.get(User, user_id)
            result = services.create_enrollment(
                session, user, EnrollmentCreate(course_id=course_id)
            )
            return "created", result.id
        except services.BusinessRuleError as exc:
            return "rejected", exc.status_code
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(enroll, range(2)))

    check = factory()
    count = check.scalar(select(func.count()).select_from(Enrollment))
    check.close()
    assert count == 1, outcomes
    assert sorted(status for status, _ in outcomes) == ["created", "rejected"]
