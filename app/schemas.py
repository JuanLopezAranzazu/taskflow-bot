from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models import TaskStatus


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    telegram_id: int
    username: str | None
    full_name: str


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    title: str
    description: str | None
    status: TaskStatus
    assignee_id: int | None
    due_date: date | None
    created_at: datetime
    updated_at: datetime


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    due_date: date | None = None
    assignee_id: int | None = None


class TaskUpdateStatus(BaseModel):
    status: TaskStatus


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None
    owner_id: int
    created_at: datetime


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
