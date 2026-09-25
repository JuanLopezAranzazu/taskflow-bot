from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app import crud
from app.bot.keyboards import (
    STATUS_LABELS,
    confirm_keyboard,
    project_menu_keyboard,
    projects_keyboard,
    skip_keyboard,
    task_detail_keyboard,
    tasks_keyboard,
)
from app.bot.states import AssignTaskStates, NewProjectStates, NewTaskStates
from app.database import AsyncSessionLocal
from app.models import TaskStatus

router = Router()

HELP_TEXT = (
    "\U0001F916 <b>Bot de seguimiento de proyectos</b>\n\n"
    "/start - Registrarte / iniciar\n"
    "/proyectos - Ver tus proyectos\n"
    "/nuevoproyecto - Crear un proyecto nuevo\n"
    "/ayuda - Ver esta ayuda\n\n"
    "Dentro de cada proyecto puedes crear tareas, asignarlas a miembros "
    "por su @usuario de Telegram, y cambiar su estado "
    "(Pendiente / En progreso / Hecha) con botones."
)


async def _get_user(message_or_cb, session):
    tg_user = message_or_cb.from_user
    return await crud.get_or_create_user(
        session, tg_user.id, tg_user.username, tg_user.full_name
    )


# ---------------- Comandos basicos ----------------

@router.message(CommandStart())
async def cmd_start(message: Message):
    async with AsyncSessionLocal() as session:
        await _get_user(message, session)
    await message.answer(
        f"\U0001F44B ¡Hola, {message.from_user.full_name}!\n\n" + HELP_TEXT
    )


@router.message(Command("ayuda"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT)


@router.message(Command("proyectos"))
async def cmd_projects(message: Message):
    async with AsyncSessionLocal() as session:
        user = await _get_user(message, session)
        projects = await crud.list_projects_for_user(session, user)
    if not projects:
        await message.answer(
            "Todavía no tienes proyectos. Usa /nuevoproyecto para crear el primero."
        )
        return
    await message.answer("\U0001F4C2 Tus proyectos:", reply_markup=projects_keyboard(projects))


# ---------------- Crear proyecto (FSM) ----------------

@router.message(Command("nuevoproyecto"))
async def cmd_new_project(message: Message, state: FSMContext):
    await state.set_state(NewProjectStates.waiting_name)
    await message.answer("Escribe el <b>nombre</b> del nuevo proyecto:")


@router.callback_query(F.data == "new_project")
async def cb_new_project(callback: CallbackQuery, state: FSMContext):
    await state.set_state(NewProjectStates.waiting_name)
    await callback.message.answer("Escribe el <b>nombre</b> del nuevo proyecto:")
    await callback.answer()


@router.message(NewProjectStates.waiting_name)
async def new_project_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(NewProjectStates.waiting_description)
    await message.answer(
        "Ahora escribe una <b>descripción</b> breve (o pulsa Omitir):",
        reply_markup=skip_keyboard("skip_project_desc"),
    )


@router.message(NewProjectStates.waiting_description)
async def new_project_description(message: Message, state: FSMContext):
    await _finish_new_project(message, state, message.text.strip())


@router.callback_query(NewProjectStates.waiting_description, F.data == "skip_project_desc")
async def new_project_description_skip(callback: CallbackQuery, state: FSMContext):
    await _finish_new_project(callback.message, state, None)
    await callback.answer()


async def _finish_new_project(message: Message, state: FSMContext, description: str | None):
    data = await state.get_data()
    await state.clear()
    async with AsyncSessionLocal() as session:
        tg_user = message.from_user
        user = await crud.get_or_create_user(session, tg_user.id, tg_user.username, tg_user.full_name)
        project = await crud.create_project(session, user, data["name"], description)
    await message.answer(
        f"\u2705 Proyecto <b>{project.name}</b> creado.",
        reply_markup=project_menu_keyboard(project.id),
    )


# ---------------- Ver proyecto / menu ----------------

@router.callback_query(F.data == "back_to_projects")
async def cb_back_to_projects(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        user = await _get_user(callback, session)
        projects = await crud.list_projects_for_user(session, user)
    if not projects:
        await callback.message.edit_text("No tienes proyectos. Usa /nuevoproyecto.")
    else:
        await callback.message.edit_text(
            "\U0001F4C2 Tus proyectos:", reply_markup=projects_keyboard(projects)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("project:"))
async def cb_view_project(callback: CallbackQuery):
    project_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        project = await crud.get_project(session, project_id)
        if not project:
            await callback.answer("Ese proyecto ya no existe.", show_alert=True)
            return
        pending = sum(1 for t in project.tasks if t.status != TaskStatus.DONE)
        done = sum(1 for t in project.tasks if t.status == TaskStatus.DONE)
    text = (
        f"\U0001F4C1 <b>{project.name}</b>\n"
        f"{project.description or '<i>Sin descripción</i>'}\n\n"
        f"Tareas: {len(project.tasks)} · Pendientes: {pending} · Hechas: {done}"
    )
    await callback.message.edit_text(text, reply_markup=project_menu_keyboard(project.id))
    await callback.answer()


@router.callback_query(F.data.startswith("del_project:"))
async def cb_delete_project_confirm(callback: CallbackQuery):
    project_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "¿Seguro que quieres eliminar este proyecto y todas sus tareas?",
        reply_markup=confirm_keyboard("del_project", project_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm:del_project:"))
async def cb_delete_project(callback: CallbackQuery):
    project_id = int(callback.data.split(":")[2])
    async with AsyncSessionLocal() as session:
        project = await crud.get_project(session, project_id)
        if project:
            await crud.delete_project(session, project)
    await callback.message.edit_text("\U0001F5D1 Proyecto eliminado.")
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Operación cancelada.")
    await callback.answer()


# ---------------- Tareas: listar y ver detalle ----------------

@router.callback_query(F.data.startswith("tasks:"))
async def cb_list_tasks(callback: CallbackQuery):
    _, project_id_str, _filter = callback.data.split(":")
    project_id = int(project_id_str)
    async with AsyncSessionLocal() as session:
        tasks = await crud.list_tasks(session, project_id)
    if not tasks:
        text = "No hay tareas todavía en este proyecto."
    else:
        text = "\U0001F4CB <b>Tareas</b> (toca una para ver detalle):"
    await callback.message.edit_text(text, reply_markup=tasks_keyboard(tasks, project_id))
    await callback.answer()


def _task_text(task, assignee_name: str | None) -> str:
    due = task.due_date.strftime("%d/%m/%Y") if task.due_date else "Sin fecha"
    return (
        f"\U0001F4CC <b>{task.title}</b>\n"
        f"{task.description or '<i>Sin descripción</i>'}\n\n"
        f"Estado: <b>{STATUS_LABELS[task.status]}</b>\n"
        f"Asignada a: {assignee_name or '<i>Sin asignar</i>'}\n"
        f"Fecha límite: {due}"
    )


@router.callback_query(F.data.startswith("task:"))
async def cb_view_task(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        task = await crud.get_task(session, task_id)
        if not task:
            await callback.answer("Esa tarea ya no existe.", show_alert=True)
            return
        assignee_name = None
        if task.assignee_id:
            from app.models import User
            from sqlalchemy import select

            res = await session.execute(select(User).where(User.id == task.assignee_id))
            u = res.scalar_one_or_none()
            assignee_name = u.full_name if u else None
    await callback.message.edit_text(
        _task_text(task, assignee_name), reply_markup=task_detail_keyboard(task)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_status:"))
async def cb_set_status(callback: CallbackQuery):
    _, task_id_str, status_str = callback.data.split(":")
    task_id = int(task_id_str)
    status = TaskStatus(status_str)
    async with AsyncSessionLocal() as session:
        task = await crud.get_task(session, task_id)
        if not task:
            await callback.answer("Esa tarea ya no existe.", show_alert=True)
            return
        task = await crud.set_task_status(session, task, status)
        assignee_name = None
        if task.assignee_id:
            from app.models import User
            from sqlalchemy import select

            res = await session.execute(select(User).where(User.id == task.assignee_id))
            u = res.scalar_one_or_none()
            assignee_name = u.full_name if u else None
    await callback.message.edit_text(
        _task_text(task, assignee_name), reply_markup=task_detail_keyboard(task)
    )
    await callback.answer(f"Estado actualizado a: {STATUS_LABELS[status]}")


@router.callback_query(F.data.startswith("del_task:"))
async def cb_delete_task(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        task = await crud.get_task(session, task_id)
        if not task:
            await callback.answer("Esa tarea ya no existe.", show_alert=True)
            return
        project_id = task.project_id
        await crud.delete_task(session, task)
        tasks = await crud.list_tasks(session, project_id)
    await callback.message.edit_text(
        "\U0001F5D1 Tarea eliminada.\n\n\U0001F4CB Tareas restantes:",
        reply_markup=tasks_keyboard(tasks, project_id),
    )
    await callback.answer()


# ---------------- Crear tarea (FSM) ----------------

@router.callback_query(F.data.startswith("new_task:"))
async def cb_new_task(callback: CallbackQuery, state: FSMContext):
    project_id = int(callback.data.split(":")[1])
    await state.set_state(NewTaskStates.waiting_title)
    await state.update_data(project_id=project_id)
    await callback.message.answer("Escribe el <b>título</b> de la nueva tarea:")
    await callback.answer()


@router.message(NewTaskStates.waiting_title)
async def new_task_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(NewTaskStates.waiting_description)
    await message.answer(
        "Escribe una <b>descripción</b> (o pulsa Omitir):",
        reply_markup=skip_keyboard("skip_task_desc"),
    )


@router.message(NewTaskStates.waiting_description)
async def new_task_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(NewTaskStates.waiting_due_date)
    await message.answer(
        "Fecha límite en formato <b>DD/MM/AAAA</b> (o pulsa Omitir):",
        reply_markup=skip_keyboard("skip_task_due"),
    )


@router.callback_query(NewTaskStates.waiting_description, F.data == "skip_task_desc")
async def new_task_description_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(description=None)
    await state.set_state(NewTaskStates.waiting_due_date)
    await callback.message.answer(
        "Fecha límite en formato <b>DD/MM/AAAA</b> (o pulsa Omitir):",
        reply_markup=skip_keyboard("skip_task_due"),
    )
    await callback.answer()


@router.message(NewTaskStates.waiting_due_date)
async def new_task_due_date(message: Message, state: FSMContext):
    try:
        due_date = datetime.strptime(message.text.strip(), "%d/%m/%Y").date()
    except ValueError:
        await message.answer("Formato inválido. Usa DD/MM/AAAA, o pulsa Omitir.")
        return
    await _finish_new_task(message, state, due_date)


@router.callback_query(NewTaskStates.waiting_due_date, F.data == "skip_task_due")
async def new_task_due_date_skip(callback: CallbackQuery, state: FSMContext):
    await _finish_new_task(callback.message, state, None)
    await callback.answer()


async def _finish_new_task(message: Message, state: FSMContext, due_date):
    data = await state.get_data()
    await state.clear()
    async with AsyncSessionLocal() as session:
        task = await crud.create_task(
            session,
            project_id=data["project_id"],
            title=data["title"],
            description=data.get("description"),
            due_date=due_date,
        )
    await message.answer(
        f"\u2705 Tarea <b>{task.title}</b> creada.",
        reply_markup=task_detail_keyboard(task),
    )


# ---------------- Asignar tarea e invitar miembros ----------------

@router.callback_query(F.data.startswith("assign_task:"))
async def cb_assign_task(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split(":")[1])
    await state.set_state(AssignTaskStates.waiting_username)
    await state.update_data(task_id=task_id)
    await callback.message.answer(
        "Envíame el <b>@usuario de Telegram</b> de la persona a la que quieres "
        "asignar la tarea (debe haber usado /start con este bot antes)."
    )
    await callback.answer()


@router.message(AssignTaskStates.waiting_username)
async def assign_task_username(message: Message, state: FSMContext):
    data = await state.get_data()
    task_id = data.get("task_id")
    invite_project_id = data.get("project_id_for_invite")

    async with AsyncSessionLocal() as session:
        target = await crud.get_user_by_username(session, message.text.strip())
        if not target:
            await message.answer(
                "No encuentro a ese usuario. Pídele que le escriba /start al bot primero "
                "e inténtalo de nuevo."
            )
            return

        if task_id is not None:
            # Flujo: asignar una tarea concreta
            task = await crud.get_task(session, task_id)
            if not task:
                await message.answer("Esa tarea ya no existe.")
                await state.clear()
                return
            is_member = await crud.is_project_member(session, task.project_id, target.id)
            if not is_member:
                await crud.add_member(session, task.project_id, target.id)
            task = await crud.assign_task(session, task, target.id)
            await state.clear()
            await message.answer(
                f"\u2705 Tarea <b>{task.title}</b> asignada a {target.full_name}.",
                reply_markup=task_detail_keyboard(task),
            )
            return

        # Flujo: invitar a alguien al proyecto (sin asignarle una tarea)
        is_member = await crud.is_project_member(session, invite_project_id, target.id)
        if is_member:
            await state.clear()
            await message.answer(f"{target.full_name} ya es miembro de este proyecto.")
            return
        await crud.add_member(session, invite_project_id, target.id)
        project = await crud.get_project(session, invite_project_id)

    await state.clear()
    await message.answer(
        f"\u2705 {target.full_name} fue añadido al proyecto <b>{project.name}</b>.",
        reply_markup=project_menu_keyboard(project.id),
    )


@router.callback_query(F.data.startswith("invite:"))
async def cb_invite_member(callback: CallbackQuery, state: FSMContext):
    project_id = int(callback.data.split(":")[1])
    await state.set_state(AssignTaskStates.waiting_username)
    await state.update_data(task_id=None, project_id_for_invite=project_id)
    await callback.message.answer(
        "Envíame el <b>@usuario de Telegram</b> de la persona que quieres invitar "
        "al proyecto (debe haber usado /start con este bot antes)."
    )
    await callback.answer()
