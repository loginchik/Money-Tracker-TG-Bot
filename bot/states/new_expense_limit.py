"""
Package contains states group for new expense limit creation.
"""

from aiogram.fsm.state import State, StatesGroup


class NewExpenseLimitStates(StatesGroup):
    """
    States group for new expense limit creation.
    """
    get_title = State()
    get_category = State()
    get_subcategory = State()
    get_period = State()
    get_current_period_start = State()
    get_limit_value = State()
    get_end_date = State()
    get_cumulative = State()

