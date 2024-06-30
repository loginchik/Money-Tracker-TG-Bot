from aiogram.fsm.state import State, StatesGroup


class DeleteExpenseLimitStates(StatesGroup):
    """
    States group for expense limit deletion process.
    """
    get_user_title = State()


class ExportStates(StatesGroup):
    """
    States group for export user's data process.
    """
    export_expenses = State()
    export_incomes = State()


class NewChoice(StatesGroup):
    get_item = State()


class NewExpenseStates(StatesGroup):
    """
    States group for new expense creation process.
    """
    get_money_amount = State()
    get_category = State()
    get_subcategory = State()
    get_datetime = State()
    get_location = State()
    get_confirmation = State()


class NewExpenseLimitStates(StatesGroup):
    """
    States group for new expense limit creation process.
    """
    get_title = State()
    get_category = State()
    get_subcategory = State()
    get_period = State()
    get_current_period_start = State()
    get_limit_value = State()
    get_end_date = State()
    get_cumulative = State()
    get_confirmation = State()


class NewIncomeStates(StatesGroup):
    """
    States group for new income creation process.
    """
    get_money_amount = State()
    get_active_status = State()
    get_event_date = State()
    get_confirmation = State()


class RegistrationStates(StatesGroup):
    """
    States group for user registration process.
    """
    preferred_language = State()
    decision = State()


class DataDeletionStates(StatesGroup):
    """
    States group for user's all data and account deletion process.
    """
    decision = State()
