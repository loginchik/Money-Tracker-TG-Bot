from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


async def generate_preferred_lang_keyboard() -> InlineKeyboardMarkup:
    ru_button = InlineKeyboardButton(text='Русский', callback_data='ru')
    en_button = InlineKeyboardButton(text='English', callback_data='en')
    keyboard = InlineKeyboardBuilder()
    keyboard.add(ru_button, en_button)
    return keyboard.as_markup()


async def generate_registration_keyboard(user_preferred_language: str) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    register = InlineKeyboardButton(text='Создать аккаунт' if user_preferred_language == 'ru' else 'Create account',
                                    callback_data='register')
    dont = InlineKeyboardButton(text='Отмена' if user_preferred_language == 'ru' else 'Cancel',
                                callback_data='cancel_register')
    keyboard.add(register, dont)
    return keyboard.as_markup()
