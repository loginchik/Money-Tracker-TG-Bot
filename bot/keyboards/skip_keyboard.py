from aiogram.utils.keyboard import InlineKeyboardMarkup, InlineKeyboardButton, InlineKeyboardBuilder


async def generate_skip_keyboard(callback_data: str, user_language_code: str) -> InlineKeyboardMarkup:
    button = InlineKeyboardButton(text='' if user_language_code == 'ru' else 'Skip', callback_data=callback_data)
    skip_keyboard = InlineKeyboardBuilder()
    skip_keyboard.add(button)
    return skip_keyboard.as_markup()