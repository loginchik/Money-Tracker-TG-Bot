"""
Package contains scripts to address delete queries to db. Supports user data deletion process.
Runs on its own router - ``delete_router`` which must be included into main router or any other router
that is included into main to be able to get and handle pending updates.
"""
import logging

import asyncpg
from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import db.user_operations
from bot.middleware.user_language import UserLanguageMiddleware
from bot.middleware.db_connection import DBConnectionMiddleware
from bot.states.registration import DataDeletionStates
from bot.keyboards.bool_keyboard import generate_bool_keyboard
from bot.filters.user_exists import UserExists
from bot.static.user_languages import USER_LANGUAGE_PREFERENCES
from bot.static.messages import DELETE_ROUTER_MESSAGES


delete_router = Router()
delete_router.message.middleware(UserLanguageMiddleware())
delete_router.callback_query.middleware(UserLanguageMiddleware())
delete_router.callback_query.middleware(DBConnectionMiddleware())


@delete_router.message(Command(commands=['delete_my_data']), ~UserExists())
async def nothing_to_delete_message(message: Message, user_lang: str):
    """
    Handler is triggered in case user requested data deletion while not being registered.
    As far as the process is impossible, user is notified about the issue.
    :param message: User message.
    :param user_lang: User language.
    :return: Message.
    """
    message_text = DELETE_ROUTER_MESSAGES['nothing_to_delete'][user_lang]
    return await message.answer(message_text)


@delete_router.message(Command(commands=['delete_my_data']), UserExists())
async def delete_user_data(message: Message, state: FSMContext, user_lang: str):
    """
    In case there is user data to delete, user is asked to confirm their decision to prevent
    accidental data deletion.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    decision_keyboard = await generate_bool_keyboard(user_lang)
    await state.set_state(DataDeletionStates.decision)
    message_text = DELETE_ROUTER_MESSAGES['confirmation'][user_lang]
    return await message.answer(message_text, reply_markup=decision_keyboard, parse_mode=ParseMode.HTML)


@delete_router.callback_query(DataDeletionStates.decision)
async def save_delete_choice(callback: CallbackQuery, state: FSMContext, user_lang: str, db_con: asyncpg.Connection):
    """
    Catches callback from user deletion decision. If user confirms their decision, all data
    in database, including tables and records, is deleted, user preferred languages is dropped
    from local data dictionary. Otherwise, data is kept.

    :param callback: Callback query.
    :param state: FSM context.
    :param user_lang: User language.
    :param db_con: Database connection.
    :return: Message.
    """
    # Remove inline keyboard anyway.
    await callback.message.edit_reply_markup(reply_markup=None)
    # User confirmed the decision.
    if callback.data == 'true':
        user_id = callback.from_user.id
        # Successful deletion.
        try:
            await db.user_operations.delete_user_data(user_id, db_con)
            del USER_LANGUAGE_PREFERENCES[user_id]
            await state.clear()
            message_text = DELETE_ROUTER_MESSAGES['success'][user_lang]
            return await callback.message.answer(message_text)
        # Internal error.
        except Exception as e:
            logging.error(e)
            message_text = DELETE_ROUTER_MESSAGES['error'][user_lang]
            await state.clear()
            return await callback.message.answer(message_text)
    # User canceled the decision.
    else:
        message_text = DELETE_ROUTER_MESSAGES['cancel'][user_lang]
        await state.clear()
        return await callback.message.answer(message_text)
