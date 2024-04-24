"""
Contains states group for user registration and data deletion processes.
States groups are in one file due to the fact that they are compact
and address the same process from different edges.
"""


from aiogram.fsm.state import StatesGroup, State


class RegistrationStates(StatesGroup):
    """
    User registration states.
    """
    preferred_language = State()
    decision = State()


class DataDeletionStates(StatesGroup):
    """
    Data deletion states.
    """
    decision = State()
