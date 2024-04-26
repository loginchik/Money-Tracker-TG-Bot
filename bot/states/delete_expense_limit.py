from aiogram.fsm.state import State, StatesGroup


class DeleteExpenseLimitStates(StatesGroup):
    get_user_title = State()
