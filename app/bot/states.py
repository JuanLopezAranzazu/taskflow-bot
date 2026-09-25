from aiogram.fsm.state import State, StatesGroup


class NewProjectStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()


class NewTaskStates(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_due_date = State()


class AssignTaskStates(StatesGroup):
    waiting_username = State()
