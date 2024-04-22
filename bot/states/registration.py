from aiogram.fsm.state import StatesGroup, State


class RegistrationStates(StatesGroup):
    """
    User registration states.
    """
    decision = State()
