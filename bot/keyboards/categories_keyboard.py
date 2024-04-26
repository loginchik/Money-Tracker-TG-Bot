import asyncpg
from aiogram.utils.keyboard import InlineKeyboardMarkup, InlineKeyboardButton, InlineKeyboardBuilder

from db.expense_operations import get_expense_categories


async def generate_categories_keyboard(user_language_code: str, db_con: asyncpg.Connection) -> InlineKeyboardMarkup:
    categories_keyboard = InlineKeyboardBuilder()
    categories = await get_expense_categories(db_con)
    title_column = 'title_ru' if user_language_code == 'ru' else 'title_en'
    for cat in categories:
        button = InlineKeyboardButton(text=cat[title_column], callback_data=f'category:{cat["id"]}')
        categories_keyboard.add(button)
    categories_keyboard.adjust(2)
    return categories_keyboard.as_markup()
