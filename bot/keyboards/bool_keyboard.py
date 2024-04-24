from aiogram.utils.keyboard import InlineKeyboardMarkup, InlineKeyboardButton, InlineKeyboardBuilder


async def generate_bool_keyboard(user_language_code: str) -> InlineKeyboardMarkup:
    yes_button = InlineKeyboardButton(text='Да' if user_language_code == 'ru' else 'Yes', callback_data='true')
    no_button = InlineKeyboardButton(text='Нет' if user_language_code == 'ru' else 'No', callback_data='false')
    keyboard = InlineKeyboardBuilder()
    keyboard.add(yes_button, no_button)
    return keyboard.as_markup()