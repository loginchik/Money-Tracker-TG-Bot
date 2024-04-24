"""
Package contains scripts to address delete queries to db. Supports user data deletion process.
Runs on its own router - ``delete_router`` which must be included into main router or any other router
that is included into main to be able to get and handle pending updates.
"""


from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import db.user_operations
from bot.middleware.user_language import UserLanguageMiddleware
from bot.states.registration import DataDeletionStates
from bot.keyboards.bool_keyboard import generate_bool_keyboard
from bot.filters.user_exists import UserExists
from bot.static.user_languages import USER_LANGUAGE_PREFERENCES


delete_router = Router()
delete_router.message.middleware(UserLanguageMiddleware())


@delete_router.message(Command(commands=['delete_my_data']), ~UserExists())
async def nothing_to_delete_message(message: Message):
    await message.answer('You are not registered, so there is no data to delete.')


@delete_router.message(Command(commands=['delete_my_data']), UserExists())
async def delete_user_data(message: Message, state: FSMContext, user_lang: str):
    decision_keyboard = await generate_bool_keyboard(user_lang)
    await state.set_state(DataDeletionStates.decision)
    await message.answer('Are you sure? The action cannot be undone.', reply_markup=decision_keyboard)


@delete_router.callback_query(DataDeletionStates.decision)
async def save_delete_choice(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    if callback.data == 'true':
        user_id = callback.from_user.id
        try:
            await db.user_operations.delete_user_data(user_id)
            del USER_LANGUAGE_PREFERENCES[user_id]
            await callback.message.answer('All data deleted.')
        except Exception as e:
            print(e)
            await callback.message.answer('Sorry, try again later')
    else:
        await callback.message.answer('We are glad you are not deleting')

    await state.clear()
