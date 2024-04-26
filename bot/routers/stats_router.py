import logging

import asyncpg
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.types.input_file import BufferedInputFile, InputFile
from aiogram.filters import Command, StateFilter

from bot.middleware.user_language import UserLanguageMiddleware
from bot.middleware.db_connection import DBConnectionMiddleware
from bot.filters.user_exists import UserExists
from bot.static.messages import STATS_ROUTER_MESSAGES
from bot.keyboards.stats_keyboard import generate_stats_keyboard
from bot.internal.stats import get_account_stats
from bot.internal.stats.expense_limits_stats import expense_limits_stats
from bot.internal.stats.last_m_expense import get_last_month_expenses

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
async def send_stats(callback: CallbackQuery, user_lang: str, db_con: asyncpg.Connection, bot: Bot):
    if callback.data == 'stats_account':
        try:
            report_message = await get_account_stats(callback.from_user.id, user_lang, db_con)
            return await callback.message.answer(report_message)
        except Exception as e:
            logging.error(e)
            message_text = STATS_ROUTER_MESSAGES['error'][user_lang]
            return await callback.message.answer(message_text)
    elif callback.data == 'stats_expense_limits':
        try:
            report_data = await expense_limits_stats(callback.from_user.id, db_con, user_lang)
            if report_data is None:
                return callback.message.answer(STATS_ROUTER_MESSAGES['empty_stats'][user_lang])

            report_text, report_img = report_data
            media = BufferedInputFile(file=report_img, filename='expense_limits.png')
            await bot.send_photo(chat_id=callback.message.chat.id, photo=media)
            return await callback.message.answer(report_text)
        except Exception as e:
            logging.error(e)
            message_text = STATS_ROUTER_MESSAGES['error'][user_lang]
            return await callback.message.answer(message_text)
    elif callback.data == 'stats_last_month_expense':
        try:
            report_data = await get_last_month_expenses(callback.from_user.id, user_lang, db_con)
            if report_data is None:
                return callback.message.answer(STATS_ROUTER_MESSAGES['empty_stats'][user_lang])

            categories_bar, subcategories_bar, day_stats = report_data
            categories_bar = BufferedInputFile(file=categories_bar, filename='categories_lm.png')
            subcategories_bar = BufferedInputFile(file=subcategories_bar, filename='subcategories.png')
            day_stats = BufferedInputFile(file=day_stats, filename='daily_stat.png')
            await bot.send_photo(chat_id=callback.message.chat.id, photo=categories_bar)
            await bot.send_photo(chat_id=callback.message.chat.id, photo=subcategories_bar)
            await bot.send_photo(chat_id=callback.message.chat.id, photo=day_stats)

        except Exception as e:
            logging.error(e)
            message_text = STATS_ROUTER_MESSAGES['error'][user_lang]
            return await callback.message.answer(message_text)
    else:
        await callback.answer(callback.data)
