from aiogram.utils.keyboard import InlineKeyboardMarkup, InlineKeyboardButton, InlineKeyboardBuilder

from db.expense_operations import get_expense_subcategories


async def generate_subcategories_keyboard(category_id: int, user_language_code: str) -> InlineKeyboardMarkup:
    subcategories_keyboard = InlineKeyboardBuilder()
    subcategories = await get_expense_subcategories(category_id)
    title_column = 'title_ru' if user_language_code == 'ru' else 'title_en'
    for sub in subcategories:
        button = InlineKeyboardButton(text=sub[title_column], callback_data=f'subcategory:{sub["id"]}')
        subcategories_keyboard.add(button)
    back_button = InlineKeyboardButton(text='Back to categories', callback_data='back')
    subcategories_keyboard.add(back_button)
    subcategories_keyboard.adjust(2)
    return subcategories_keyboard.as_markup()