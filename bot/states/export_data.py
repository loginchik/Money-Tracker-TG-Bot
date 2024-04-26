from aiogram.fsm.state import State, StatesGroup


class ExportStates(StatesGroup):
    export_expenses = State()
    export_incomes = State()
