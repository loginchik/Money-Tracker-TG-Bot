import logging
import os
import datetime as dt

import asyncpg
from aiogram import Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile, InputMediaDocument
from aiogram.filters import Command, StateFilter

from bot.filters.user_exists import UserExists
from bot.middleware.user_language import UserLanguageMiddleware
from bot.middleware.db_connection import DBConnectionMiddleware
from bot.static.messages import EXPORT_ROUTER_MESSAGES
from bot.states.export_data import ExportStates
import db.expense_operations
import db.income_operations

export_router = Router()
export_router.message.middleware(UserLanguageMiddleware())
export_router.message.middleware(DBConnectionMiddleware())


@export_router.message(Command('export_my_data'), ~UserExists(), StateFilter(None))
async def no_export(message: Message, user_lang: str):
    message_text = EXPORT_ROUTER_MESSAGES['not_registered'][user_lang]
    await message.answer(message_text)


async def export_expenses(message: Message, user_id: int, user_lang: str, bot: Bot, state: FSMContext,
                          db_con: asyncpg.Connection) -> bool:
    exp_temp_filename = f'{user_id}_{dt.datetime.now().strftime("%d%H%M%S")}_expenses'
    exp_temp_filename_gpkg = exp_temp_filename + '.gpkg'
    exp_temp_filename_csv = exp_temp_filename + '.csv'
    try:
        # Save expenses data in files
        expenses_data = await db.expense_operations.get_user_expenses(user_id, user_lang, db_con)
        if expenses_data is None:
            raise AttributeError('No expenses data')
        expenses_data.to_file(exp_temp_filename_gpkg)
        expenses_data.to_file(exp_temp_filename_csv, encoding='utf-8', driver='CSV', geometry='AS_WKT')

        # Send expenses
        exp_filename_csv = f'{dt.datetime.now().strftime("%d_%m_%Y_%H_%M_%S")}_expenses_data.csv'
        exp_filename_gpkg = f'{dt.datetime.now().strftime("%d_%m_%Y_%H_%M_%S")}_expenses_data.gpkg'
        fs_csv = FSInputFile(path=exp_temp_filename_csv, filename=exp_filename_csv)
        fs_gpkg = FSInputFile(path=exp_temp_filename_gpkg, filename=exp_filename_gpkg)
        export_expenses_text = EXPORT_ROUTER_MESSAGES['success_expense'][user_lang]
        await bot.send_media_group(chat_id=message.chat.id,
                                   media=[InputMediaDocument(media=fs_csv), InputMediaDocument(media=fs_gpkg)])
        await bot.send_message(chat_id=message.chat.id, text=export_expenses_text)
        return True
    except Exception as e:
        logging.error(e)
        error_message = EXPORT_ROUTER_MESSAGES['error_expense'][user_lang]
        await message.answer(error_message)
        return False
    finally:
        # Remove temp files
        for temp_file in [exp_temp_filename_gpkg, exp_temp_filename_csv]:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        # Set state on exporting incomes
        await state.set_state(ExportStates.export_incomes)


async def export_incomes(message: Message, user_id: int, user_lang: str, bot: Bot, state: FSMContext,
                         db_con: asyncpg.Connection) -> bool:
    income_temp_filename = f'{user_id}_{dt.datetime.now().strftime("%d%H%M%S")}_expenses.csv'
    income_out_filename = f'{dt.datetime.now().strftime("%d_%m_%Y_%H_%M_%S")}_expenses_incomes.csv'
    try:
        incomes_data = await db.income_operations.get_user_income(user_id, db_con)
        if incomes_data is None:
            raise AttributeError('No incomes data')
        incomes_data.to_csv(income_temp_filename, index=False)
        fs = FSInputFile(path=income_temp_filename, filename=income_out_filename)
        await bot.send_document(chat_id=message.chat.id, document=fs)
        export_incomes_text = EXPORT_ROUTER_MESSAGES['success_income'][user_lang]
        await message.answer(export_incomes_text)
        return True
    except Exception as e:
        logging.error(e)
        error_message = EXPORT_ROUTER_MESSAGES['error_income'][user_lang]
        await message.answer(error_message)
        return False
    finally:
        # Remove temp file
        if os.path.exists(income_temp_filename):
            os.remove(income_temp_filename)
        # Clear the state
        await state.clear()


@export_router.message(Command('export_my_data'), UserExists(), StateFilter(None))
async def export_users_data(message: Message, user_lang: str, state: FSMContext, bot: Bot, db_con: asyncpg.Connection):
    user_id = message.from_user.id
    wait_message_text = EXPORT_ROUTER_MESSAGES['wait'][user_lang]
    await message.answer(wait_message_text)
    await state.set_state(ExportStates.export_expenses)

    try:
        expense_success = await export_expenses(message, user_id, user_lang, bot, state, db_con)
    except Exception as e:
        logging.error(e)
        expense_success = False
    try:
        income_success = await export_incomes(message, user_id, user_lang, bot, state, db_con)
    except Exception as e:
        logging.error(e)
        income_success = False

    if not any([income_success, expense_success]):
        total_error_message_text = EXPORT_ROUTER_MESSAGES['fail'][user_lang]
        await message.answer(total_error_message_text)


@export_router.message(ExportStates.export_expenses)
async def exporting_expenses_message(message: Message, user_lang: str, state: FSMContext):
    message_text = EXPORT_ROUTER_MESSAGES['expense_wait'][user_lang]
    await message.answer(message_text)


@export_router.message(ExportStates.export_incomes)
async def export_incomes_message(message: Message, user_lang: str, state: FSMContext):
    message_text = EXPORT_ROUTER_MESSAGES['income_wait'][user_lang]
    await message.answer(message_text)