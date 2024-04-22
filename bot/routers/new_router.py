from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.types.inline_keyboard_button import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

import db.user_operations
from bot.filters.user_exists import UserExists
from ..states.registration import RegistrationStates
from ..states.new_income import NewIncomeStates
from ..states.new_expense import NewExpenseStates


# Router to handle new records creation process
new_record_router = Router()


register_inline_button_ru = InlineKeyboardButton(text='Создать аккаунт', callback_data='register')
dont_register_inline_button_ru = InlineKeyboardButton(text='Отмена', callback_data='cancel_register')
register_inline_button_en = InlineKeyboardButton(text='Create account', callback_data='register')
dont_register_inline_button_en = InlineKeyboardButton(text='Cancel', callback_data='cancel_register')


# If user is not registered, one is asked to register first
@new_record_router.message(Command(commands='add_expense'), ~UserExists())
@new_record_router.message(Command(commands='add_income'), ~UserExists())
async def add_expense(message: Message, state: FSMContext):
    """
    As fas as user is not registered, one gets notified and asked if they want to register.

    :param message: Message from user, containing command.
    :param state: FSM context to set state.
    :return: Message with inline keyboard about registration.
    """

    # Construct reply markup
    reply_inline_keyboard = InlineKeyboardBuilder()
    if message.from_user.language_code == 'ru':
        reply_inline_keyboard.add(register_inline_button_ru)
        reply_inline_keyboard.add(dont_register_inline_button_ru)
    else:
        reply_inline_keyboard.add(register_inline_button_en)
        reply_inline_keyboard.add(dont_register_inline_button_en)

    await state.set_state(RegistrationStates.decision)
    await state.set_data({'command': message.text})
    await message.answer('You are not registered yet', reply_markup=reply_inline_keyboard.as_markup())


@new_record_router.callback_query(RegistrationStates.decision)
async def user_registration_decision(callback: CallbackQuery, state: FSMContext):
    """
    Gets user decision in terms of registration. If user want to register, adds their data to db
    and continues initial command process. Otherwise, doesn't register the user and notifies
    about user unavailability to continue.

    :param callback: Callback query from registration inline keyboard.
    :param state: Current FSM context.
    :return: Message.
    """

    # Get user decision from callback
    decision = callback.data
    # Remove markup from message to prevent button re-pushing
    await callback.message.edit_reply_markup(reply_markup=None)
    if decision == 'register':
        # Gather user data to insert into DB
        user_data = {
            'tg_id': callback.from_user.id,
            'tg_username': callback.from_user.username,
            'tg_first_name': callback.from_user.first_name,
        }
        # Create user and notify the user
        await db.user_operations.create_user(**user_data)
        await callback.answer('You are registered successfully.')

        # Get initial command to continue process after registration
        state_data = await state.get_data()
        initial_command = state_data['command']
        # Define function to continue process
        if initial_command == '/add_expense':
            await add_expense_init(message=callback.message)
        elif initial_command == '/add_income':
            await add_income_init(message=callback.message)

    elif decision == 'cancel_register':
        # Notify the user
        await callback.message.answer('Sorry, you have to register to get access to bot :_(')

    # Clear state and state data
    await state.clear()


# If user is registered, process starts
@new_record_router.message(Command(commands=['add_expense']), UserExists())
async def add_expense_init(message: Message):
    await message.answer('New expense creation started')


# If user is registered, process starts
@new_record_router.message(Command(commands=['add_income']), UserExists())
async def add_income_init(message: Message):
    await message.answer('New income creation started')

