"""Idempotent database initialisation and demo data for local/docker runs."""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.db import Base, SessionLocal, engine
from app.models import Course, Enrollment, Session, Tag, User
from app.security import hash_password

DEMO_USERS = [
    ("admin@eduflow.com", "admin123", "Admin Principal", "admin"),
    ("formateur@eduflow.com", "form1234", "Formateur Test", "formateur"),
    ("apprenant@eduflow.com", "apprenant123", "Apprenant Test", "apprenant"),
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        if db.query(User).count():
            return
        users = []
        for email, password, name, role in DEMO_USERS:
            user = User(
                email=email, full_name=name, role=role,
                hashed_password=hash_password(password),
            )
            db.add(user)
            users.append(user)
        db.flush()
        tags = [Tag(name=name) for name in ("python", "qualite", "devops", "web")]
        db.add_all(tags)
        db.flush()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        courses = []
        for index, title in enumerate(("Qualite logicielle ISO 25010", "Tests automatises Python", "DevOps et CI/CD")):
            course = Course(
                title=title,
                description=f"Description de {title}",
                capacity=10,
                status="published",
                owner_id=users[1].id,
                tags=[tags[index], tags[(index + 1) % len(tags)]],
            )
            db.add(course)
            courses.append(course)
        db.flush()
        for course in courses:
            session = Session(
                course_id=course.id,
                starts_at=now - timedelta(days=1),
                ends_at=now + timedelta(days=30),
                room="Salle A",
                capacity=10,
            )
            db.add(session)
            db.flush()
            db.add(Enrollment(
                user_id=users[2].id, course_id=course.id, session_id=session.id,
                status="validated",
            ))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Seed complete")
