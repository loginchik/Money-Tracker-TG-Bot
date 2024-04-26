import logging

import asyncpg
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter

from bot.middleware.user_language import UserLanguageMiddleware
from bot.middleware.db_connection import DBConnectionMiddleware
from bot.filters.user_exists import UserExists
from bot.static.messages import STATS_ROUTER_MESSAGES
from bot.keyboards.stats_keyboard import generate_stats_keyboard
from bot.internal.stats import get_account_stats

stats_router = Router()
stats_router.message.middleware(UserLanguageMiddleware())
stats_router.callback_query.middleware(UserLanguageMiddleware())
stats_router.callback_query.middleware(DBConnectionMiddleware())


@stats_router.message(Command(commands=['stats']), ~UserExists(), StateFilter(None))
async def no_stats_message(message: Message, user_lang: str):
    """
    Sends a message with no statistics.
    :param message: User message.
    :param user_lang: User language.
    :return: Message.
    """
    message_text = STATS_ROUTER_MESSAGES['no_stats'][user_lang]
    return await message.answer(message_text)


@stats_router.message(Command(commands=['stats']), UserExists(), StateFilter(None))
async def stats_choice(message: Message, user_lang: str):
    keyboard = await generate_stats_keyboard(user_lang)
    message_text = STATS_ROUTER_MESSAGES['choice'][user_lang]
    return await message.answer(message_text, reply_markup=keyboard)


@stats_router.callback_query(F.data.startswith('stats_'), UserExists(), StateFilter(None))
async def send_stats(callback: CallbackQuery, user_lang: str, db_con: asyncpg.Connection):
    if callback.data == 'stats_account':
        try:
            report_message = await get_account_stats(callback.from_user.id, user_lang, db_con)
            return await callback.message.answer(report_message)
        except Exception as e:
            logging.error(e)
            message_text = STATS_ROUTER_MESSAGES['error'][user_lang]
            return await callback.message.answer(message_text)
    else:
        await callback.answer(callback.data)
