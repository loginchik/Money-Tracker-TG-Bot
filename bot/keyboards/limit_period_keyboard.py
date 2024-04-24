from aiogram.utils.keyboard import InlineKeyboardMarkup, InlineKeyboardButton, InlineKeyboardBuilder


async def generate_period_keyboard(user_language_code: str) -> InlineKeyboardMarkup:
    week = InlineKeyboardButton(text='7 дней' if user_language_code == 'ru' else '7 days', callback_data='period:1')
    month = InlineKeyboardButton(text='30 дней' if user_language_code == 'ru' else '30 days', callback_data='period:2')
    year = InlineKeyboardButton(text='365 дней' if user_language_code == 'ru' else '365 days', callback_data='period:3')

    keyboard = InlineKeyboardBuilder()
    keyboard.add(week)
    keyboard.add(month)
    keyboard.add(year)
    keyboard.adjust(1)
    return keyboard.as_markup()