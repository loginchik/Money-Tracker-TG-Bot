"""
Contains states group for new expense creation process.
"""

from aiogram.fsm.state import StatesGroup, State


class NewExpenseStates(StatesGroup):
    get_money_amount = State()
    get_category = State()
    get_subcategory = State()
    get_datetime = State()
    get_location = State()
