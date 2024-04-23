import re
import datetime as dt

from aiogram import Router, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.types.inline_keyboard_button import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

import db.user_operations
from bot.filters.user_exists import UserExists
from bot.states.registration import RegistrationStates
from bot.states.new_income import NewIncomeStates
from bot.states.new_expense import NewExpenseStates


# Router to handle new records creation process
new_record_router = Router()


register_inline_button_ru = InlineKeyboardButton(text='Создать аккаунт', callback_data='register')
dont_register_inline_button_ru = InlineKeyboardButton(text='Отмена', callback_data='cancel_register')
register_inline_button_en = InlineKeyboardButton(text='Create account', callback_data='register')
dont_register_inline_button_en = InlineKeyboardButton(text='Cancel', callback_data='cancel_register')


@new_record_router.message(Command(commands=['abort']))
async def abort_process(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer('Process aborted')


# If user is not registered, one is asked to register first
@new_record_router.message(Command(commands='add_expense'), ~UserExists(), StateFilter(None))
@new_record_router.message(Command(commands='add_income'), ~UserExists(), StateFilter(None))
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
@new_record_router.message(Command(commands=['add_expense']), UserExists(), StateFilter(None))
async def add_expense_init(message: Message):
    await message.answer('New expense creation started')


# If user is registered, process starts
@new_record_router.message(Command(commands=['add_income']), UserExists(), StateFilter(None))
async def add_income_init(message: Message, state: FSMContext):
    """
    Sets state to NewIncomeStates.get_money_amount and asks for money amount.
    :param message: Message from user.
    :param state: FSM context to set state.
    :return: Message.
    """
    await state.set_state(NewIncomeStates.get_money_amount)
    await message.answer('Money amount')


async def get_income_active_status(message: Message, state: FSMContext):
    """
    Sets state to NewIncomeStates.get_active_status and asks for active/passive income status.
    :param message: Message from user.
    :param state: FSM context to set state.
    :return: Message with inline keyboard markup.
    """
    await state.set_state(NewIncomeStates.get_active_status)
    active_status_inline_keyboard = InlineKeyboardBuilder()
    active_status_inline_keyboard.add(InlineKeyboardButton(text='Active', callback_data='active'))
    active_status_inline_keyboard.add(InlineKeyboardButton(text='Passive', callback_data='passive'))
    await message.answer('Active status', reply_markup=active_status_inline_keyboard.as_markup())


@new_record_router.message(NewIncomeStates.get_money_amount)
async def save_money_amount(message: Message, state: FSMContext):
    """
    Checks if money amount from user message can be converted into positive number. If so,
    saves the value to state data and redirects to get_income_active_status. Otherwise,
    asks for correct money amount.
    :param message: User message.
    :param state: FSM context.
    :return: Message.
    """
    raw_money_amount = message.text.strip()
    try:
        raw_money_amount = raw_money_amount.replace(',', '.')
        money_amount = float(raw_money_amount)
        if money_amount > 0:
            await state.update_data({'amount': money_amount})
            await get_income_active_status(message, state)
        else:
            await message.answer('Sorry, money amount cannot be negative.')
    except (ValueError, Exception):
        await message.answer('Please send a number without, like 123.45 or 123')


async def get_income_date(message: Message, state: FSMContext):
    """
    Asks for income date.
    :param message: Message from user.
    :param state: FSM context.
    :return: Message with 'today' button.
    """
    await state.set_state(NewIncomeStates.get_event_date)
    today_markup = InlineKeyboardBuilder()
    today_markup.add(InlineKeyboardButton(text='Today', callback_data='today'))
    await message.answer('Event date like 01.12.2024', reply_markup=today_markup.as_markup())


@new_record_router.callback_query(NewIncomeStates.get_active_status)
async def save_income_active_status(callback: CallbackQuery, state: FSMContext):
    """
    Converts user inline choice into boolean and redirects to get_income_date.
    :param callback: User callback choice from active/passive income status keyboard.
    :param state: FSM context.
    :return: Message.
    """
    await state.update_data({'passive': callback.data == 'passive'})
    await callback.message.edit_reply_markup(reply_markup=None)
    await get_income_date(callback.message, state)


async def save_income_data_to_db(message: Message, state: FSMContext):
    """
    Saves income data to DB and finished the creation process.
    :param message: Message from user.
    :param state: FSM context.
    :return: Message.
    """
    total_data = await state.get_data()
    await message.answer(str(total_data))
    await state.clear()
    print(await state.get_data())


@new_record_router.callback_query(NewIncomeStates.get_event_date)
async def save_income_date_from_callback(callback: CallbackQuery, state: FSMContext):
    """
    Saves today's date as event date into income data dict and redirects to get_income_date.
    Keyboard is hidden after push.
    :param callback: User push button event.
    :param state: FSM context.
    :return: Message.
    """
    if callback.data == 'today':
        await state.update_data({'event_date': dt.date.today()})
    await callback.message.edit_reply_markup(reply_markup=None)
    await save_income_data_to_db(callback.message, state)


@new_record_router.message(NewIncomeStates.get_event_date)
async def save_income_date_from_message(message: Message, state: FSMContext, bot: Bot):
    """
    Tries to extract date string from user message. If successful, redirects to save_income_data_to_db.
    Otherwise, asks for correct date.

    :param message: Message from user.
    :param state: FSM context.
    :return: Message.
    """
    def check_date(date: dt.date) -> bool:
        return dt.date.today() >= date

    # Remove 'today' button anyway
    try:
        await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.message_id - 1, reply_markup=None)
    except TelegramBadRequest:
        pass

    raw_event_date = message.text.strip()
    try:
        # Immediate convert
        event_date = dt.datetime.strptime(raw_event_date, '%d.%m.%Y').date()
        if check_date(event_date):
            await state.update_data({'event_date': event_date})
        else:
            await message.answer('This date has not happened yet')
            return
    except ValueError:
        # Extract date string and convert it
        date_pattern = r'(\d{1,2}\.\d{1,2}\.\d{4})'
        try:
            date_string_from_message = re.search(date_pattern, raw_event_date).group(1)
            event_date = dt.datetime.strptime(date_string_from_message, '%d.%m.%Y').date()
            if check_date(event_date):
                await state.update_data({'event_date': event_date})
            else:
                await message.answer('This date has not happened yet')
                return
        except (AttributeError, Exception):
            # Failed both times
            await message.answer('Please send a correct date in format 01.12.2023')
            return

    # Save collected data to db
    await save_income_data_to_db(message, state)
