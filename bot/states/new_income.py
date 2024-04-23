"""
Contains states group for new income creation process.
"""

from aiogram.fsm.state import State, StatesGroup


class NewIncomeStates(StatesGroup):
    get_money_amount = State()
    get_active_status = State()
    get_event_date = State()
