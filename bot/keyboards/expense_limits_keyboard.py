import asyncpg
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.expense_limit_operations import user_expense_limits


async def generate_expense_limits_keyboard(user_id: int, db_connection: asyncpg.connection,
                                           user_lang: str) -> InlineKeyboardMarkup | None:
    limits = await user_expense_limits(user_id, db_connection)
    if len(limits) == 0:
        return None
    keyboard = InlineKeyboardBuilder()
    keyboard.add(*[InlineKeyboardButton(text=lim, callback_data=lim) for lim in limits])
    cancel_button = InlineKeyboardButton(text='Отмена' if user_lang == 'ru' else 'Cancel',
                                         callback_data='cancel_limit_delete')
    keyboard.add(cancel_button)
    keyboard.adjust(1)
    return keyboard.as_markup()
