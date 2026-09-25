from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.models import Project, Task, TaskStatus

STATUS_LABELS = {
    TaskStatus.TODO: "Pendiente",
    TaskStatus.IN_PROGRESS: "En progreso",
    TaskStatus.DONE: "Hecha",
}

STATUS_EMOJI = {
    TaskStatus.TODO: "\U0001F7E5",       # cuadro rojo
    TaskStatus.IN_PROGRESS: "\U0001F7E8",  # cuadro amarillo
    TaskStatus.DONE: "\U00002705",       # check verde
}


def projects_keyboard(projects: list[Project]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"\U0001F4C1 {p.name}", callback_data=f"project:{p.id}")]
        for p in projects
    ]
    rows.append([InlineKeyboardButton(text="\u2795 Nuevo proyecto", callback_data="new_project")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def project_menu_keyboard(project_id: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="\U0001F4CB Ver tareas", callback_data=f"tasks:{project_id}:all")],
        [InlineKeyboardButton(text="\u2795 Nueva tarea", callback_data=f"new_task:{project_id}")],
        [InlineKeyboardButton(text="\U0001F465 Invitar miembro", callback_data=f"invite:{project_id}")],
        [InlineKeyboardButton(text="\U0001F5D1 Eliminar proyecto", callback_data=f"del_project:{project_id}")],
        [InlineKeyboardButton(text="\u2B05 Mis proyectos", callback_data="back_to_projects")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tasks_keyboard(tasks: list[Task], project_id: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{STATUS_EMOJI[t.status]} {t.title}",
                callback_data=f"task:{t.id}",
            )
        ]
        for t in tasks
    ]
    rows.append([InlineKeyboardButton(text="\u2795 Nueva tarea", callback_data=f"new_task:{project_id}")])
    rows.append([InlineKeyboardButton(text="\u2B05 Volver al proyecto", callback_data=f"project:{project_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def task_detail_keyboard(task: Task) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="\U0001F7E5 Pendiente", callback_data=f"set_status:{task.id}:todo"),
            InlineKeyboardButton(text="\U0001F7E8 En progreso", callback_data=f"set_status:{task.id}:in_progress"),
            InlineKeyboardButton(text="\u2705 Hecha", callback_data=f"set_status:{task.id}:done"),
        ],
        [InlineKeyboardButton(text="\U0001F464 Asignar", callback_data=f"assign_task:{task.id}")],
        [InlineKeyboardButton(text="\U0001F5D1 Eliminar tarea", callback_data=f"del_task:{task.id}")],
        [InlineKeyboardButton(text="\u2B05 Volver a tareas", callback_data=f"tasks:{task.project_id}:all")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_keyboard(action: str, entity_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="\u2705 Confirmar", callback_data=f"confirm:{action}:{entity_id}"),
                InlineKeyboardButton(text="\u274C Cancelar", callback_data="cancel"),
            ]
        ]
    )


def skip_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Omitir", callback_data=callback_data)]]
    )
