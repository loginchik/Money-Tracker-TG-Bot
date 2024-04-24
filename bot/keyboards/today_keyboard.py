from aiogram.utils.keyboard import InlineKeyboardMarkup, InlineKeyboardButton, InlineKeyboardBuilder


async def generate_today_keyboard(user_language_code: str) -> InlineKeyboardMarkup:
    today_markup = InlineKeyboardBuilder()
    button = InlineKeyboardButton(text='Сегодня' if user_language_code == 'ru' else 'Today', callback_data='today')
    today_markup.add(button)
    return today_markup.as_markup()


async def generate_now_keyboard(user_language_code: str) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    button = InlineKeyboardButton(text='Только что' if user_language_code == 'ru' else 'Just now', callback_data='now')
    keyboard.add(button)
    return keyboard.as_markup()
