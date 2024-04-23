from aiogram.utils.keyboard import InlineKeyboardMarkup, InlineKeyboardButton, InlineKeyboardBuilder


async def generate_period_keyboard(user_language_code: str) -> InlineKeyboardMarkup:
    week = InlineKeyboardButton(text='Неделя' if user_language_code == 'ru' else 'Week', callback_data='period:1')
    month = InlineKeyboardButton(text='Месяц' if user_language_code == 'ru' else 'Month', callback_data='period:2')
    year = InlineKeyboardButton(text='Год' if user_language_code == 'ru' else 'Year', callback_data='period:3')

    keyboard = InlineKeyboardBuilder()
    keyboard.add(week)
    keyboard.add(month)
    keyboard.add(year)
    keyboard.adjust(1)
    return keyboard.as_markup()