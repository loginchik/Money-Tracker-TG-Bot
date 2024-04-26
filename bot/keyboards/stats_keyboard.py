from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


async def generate_stats_keyboard(user_lang: str) -> InlineKeyboardMarkup:

    user_stats = InlineKeyboardButton(
        text='Аккаунт' if user_lang == 'ru' else 'Account',
        callback_data='stats_account'
    )
    last_month_expense = InlineKeyboardButton(
        text='Расходы за последний месяц' if user_lang == 'ru' else 'This month expenses',
        callback_data='stats_last_month_expense'
    )
    last_month_income = InlineKeyboardButton(
        text='Доходы за последний месяц' if user_lang == 'ru' else 'This month incomes',
        callback_data='stats_last_month_income'
    )

    keyboard = InlineKeyboardBuilder()
    keyboard.add(user_stats, last_month_expense, last_month_income)
    keyboard.adjust(1)
    return keyboard.as_markup()
