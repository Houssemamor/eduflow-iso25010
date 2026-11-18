"""Pydantic request/response contracts. Validation happens at the boundary."""
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=2, max_length=120)
    role: str = Field(default="apprenant", pattern="^(admin|formateur|apprenant)$")


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    role: str | None = Field(default=None, pattern="^(admin|formateur|apprenant)$")
    is_active: bool | None = None


class UserOut(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class TagCreate(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    color: str | None = Field(default=None, max_length=20)


class TagOut(ORMModel):
    id: int
    name: str
    color: str | None


class CourseCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=4000)
    capacity: int = Field(default=20, ge=1, le=1000)
    status: str = Field(default="draft", pattern="^(draft|published|archived)$")
    tag_ids: list[int] = Field(default_factory=list)

    @field_validator("tag_ids")
    @classmethod
    def unique_tags(cls, values: list[int]) -> list[int]:
        if len(values) != len(set(values)):
            raise ValueError("tag_ids must be unique")
        return values


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    capacity: int | None = Field(default=None, ge=1, le=1000)
    status: str | None = Field(default=None, pattern="^(draft|published|archived)$")
    tag_ids: list[int] | None = None


class CourseOut(ORMModel):
    id: int
    title: str
    description: str
    capacity: int
    status: str
    owner_id: int
    created_at: datetime
    tags: list[TagOut] = Field(default_factory=list)


class SessionCreate(BaseModel):
    course_id: int
    starts_at: datetime
    ends_at: datetime
    room: str = Field(default="", max_length=60)
    capacity: int = Field(default=20, ge=1, le=1000)


class SessionUpdate(BaseModel):
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    room: str | None = Field(default=None, max_length=60)
    capacity: int | None = Field(default=None, ge=1, le=1000)


class SessionOut(ORMModel):
    id: int
    course_id: int
    starts_at: datetime
    ends_at: datetime
    room: str
    capacity: int


class EnrollmentCreate(BaseModel):
    course_id: int
    session_id: int | None = None


class EnrollmentStatusUpdate(BaseModel):
    status: str = Field(pattern="^(validated|completed|cancelled)$")


class EnrollmentOut(ORMModel):
    id: int
    user_id: int
    course_id: int
    session_id: int | None
    status: str
    created_at: datetime
    updated_at: datetime


class DashboardOut(BaseModel):
    total_courses: int
    total_enrollments: int
    pending: int
    validated: int
    completed: int
    cancelled: int
    occupancy_rate: float
    by_course: list[dict]
    recent_audit: list[dict]


class AuditOut(ORMModel):
    id: int
    actor_id: int | None
    action: str
    target_type: str
    target_id: str | None
    detail: str
    created_at: datetime


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int


TokenOut.model_rebuild()
