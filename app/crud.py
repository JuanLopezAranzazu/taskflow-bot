from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import MemberRole, Project, ProjectMember, Task, TaskStatus, User


# ---------- Users ----------

async def get_or_create_user(
    session: AsyncSession, telegram_id: int, username: str | None, full_name: str
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        changed = False
        if user.username != username:
            user.username = username
            changed = True
        if user.full_name != full_name:
            user.full_name = full_name
            changed = True
        if changed:
            await session.commit()
        return user

    user = User(telegram_id=telegram_id, username=username, full_name=full_name)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    username = username.lstrip("@")
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


# ---------- Projects ----------

async def create_project(
    session: AsyncSession, owner: User, name: str, description: str | None
) -> Project:
    project = Project(name=name, description=description, owner_id=owner.id)
    session.add(project)
    await session.flush()
    session.add(ProjectMember(project_id=project.id, user_id=owner.id, role=MemberRole.OWNER))
    await session.commit()
    await session.refresh(project)
    return project


async def list_projects_for_user(session: AsyncSession, user: User) -> list[Project]:
    result = await session.execute(
        select(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user.id)
        .order_by(Project.created_at.desc())
    )
    return list(result.scalars().unique().all())


async def get_project(session: AsyncSession, project_id: int) -> Project | None:
    result = await session.execute(
        select(Project)
        .options(selectinload(Project.tasks), selectinload(Project.members))
        .where(Project.id == project_id)
    )
    return result.scalar_one_or_none()


async def is_project_member(session: AsyncSession, project_id: int, user_id: int) -> bool:
    result = await session.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
        )
    )
    return result.scalar_one_or_none() is not None


async def add_member(session: AsyncSession, project_id: int, user_id: int) -> ProjectMember:
    member = ProjectMember(project_id=project_id, user_id=user_id, role=MemberRole.MEMBER)
    session.add(member)
    await session.commit()
    await session.refresh(member)
    return member


async def delete_project(session: AsyncSession, project: Project) -> None:
    await session.delete(project)
    await session.commit()


# ---------- Tasks ----------

async def create_task(
    session: AsyncSession,
    project_id: int,
    title: str,
    description: str | None = None,
    due_date: date | None = None,
    assignee_id: int | None = None,
) -> Task:
    task = Task(
        project_id=project_id,
        title=title,
        description=description,
        due_date=due_date,
        assignee_id=assignee_id,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def list_tasks(
    session: AsyncSession, project_id: int, status: TaskStatus | None = None
) -> list[Task]:
    stmt = select(Task).where(Task.project_id == project_id)
    if status:
        stmt = stmt.where(Task.status == status)
    stmt = stmt.order_by(Task.created_at.asc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_task(session: AsyncSession, task_id: int) -> Task | None:
    result = await session.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def set_task_status(session: AsyncSession, task: Task, status: TaskStatus) -> Task:
    task.status = status
    await session.commit()
    await session.refresh(task)
    return task


async def assign_task(session: AsyncSession, task: Task, assignee_id: int | None) -> Task:
    task.assignee_id = assignee_id
    await session.commit()
    await session.refresh(task)
    return task


async def delete_task(session: AsyncSession, task: Task) -> None:
    await session.delete(task)
    await session.commit()
