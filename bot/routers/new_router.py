"""
Package contains scripts to add new records to db from user data. Package runs on its own router - ``new_record_router``
which must be included into main router or any other included into main router to be able to get and handle
pending updates.

First section is dedicated to `new expense record`, the main functionality of the bot. Second section is dedicated
to `income record creation`. Third section is dedicated to `create expense limit records`. All sections are handled
by ``new_record_router``.
"""

import datetime as dt

from aiogram import Router, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.types.inline_keyboard_button import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

import db.user_operations
import db.income_operations
import db.expense_operations
from bot.filters.user_exists import UserExists
from bot.states.registration import RegistrationStates
from bot.states.new_income import NewIncomeStates
from bot.states.new_expense import NewExpenseStates
from bot.internal import check_input

# Router to handle new records creation process
new_record_router = Router()


register_inline_button_ru = InlineKeyboardButton(text='Создать аккаунт', callback_data='register')
dont_register_inline_button_ru = InlineKeyboardButton(text='Отмена', callback_data='cancel_register')
register_inline_button_en = InlineKeyboardButton(text='Create account', callback_data='register')
dont_register_inline_button_en = InlineKeyboardButton(text='Cancel', callback_data='cancel_register')


"""
============ Abort the process ============
"""


@new_record_router.message(Command(commands=['abort']), ~StateFilter(None))
async def abort_process(message: Message, state: FSMContext):
    """
    If any state is set, aborts the process and clears the state.
    :param message: User message.
    :param state: FSM context.
    :return: Message.
    """
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer('Process aborted')


"""
============ User registration ============
"""


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
        try:
            await db.user_operations.create_user(**user_data)
            state_data = await state.get_data()
            initial_command = state_data['command']
            await callback.answer(f'You are registered successfully.')
            await callback.message.answer(initial_command)
            await state.clear()
        except Exception as e:
            await callback.answer('Something went wrong. Please try again later')
            await state.clear()
            return

    elif decision == 'cancel_register':
        # Notify the user
        await callback.message.answer('Sorry, you have to register to get access to bot :_(')
        await state.clear()


"""
============ New expense ============
"""


# If user is registered, process starts
@new_record_router.message(Command(commands=['add_expense']), UserExists(), StateFilter(None))
async def add_expense_init(message: Message, state: FSMContext):
    """
    Sets state to NewExpenseStates.get_money_amount and asks for money amount input.
    :param message: User message.
    :param state: FSM context.
    :return: Message.
    """
    await state.clear()
    await state.set_state(NewExpenseStates.get_money_amount)
    await state.update_data(user_id=message.from_user.id)
    await message.answer('Money amount')


async def get_expense_category(message: Message, state: FSMContext):
    """
    Generates categories inline keyboard and sends it to user.
    :param message: User message.
    :param state: FSM context.
    :return: Message with inline keyboard.
    """
    categories_keyboard = InlineKeyboardBuilder()
    categories = await db.expense_operations.get_expense_categories()
    title_column = 'title_ru' if message.from_user.language_code == 'ru' else 'title_en'
    for cat in categories:
        button = InlineKeyboardButton(text=cat[title_column], callback_data=f'category:{cat["id"]}')
        categories_keyboard.add(button)
    categories_keyboard.adjust(2)
    await message.answer('Chose category', reply_markup=categories_keyboard.as_markup())
    await state.set_state(NewExpenseStates.get_category)


@new_record_router.message(NewExpenseStates.get_money_amount)
async def save_expense_amount(message: Message, state: FSMContext):
    """
    Saves money count if its correct and redirects to get_expense_category.
    :param message: User message text.
    :param state: FSM context.
    :return: Message.
    """
    raw_money_count = message.text.strip()
    money_amount, error_text = check_input.money_amount_from_user_message(raw_money_count)
    if money_amount is not None:
        await state.update_data(amount=money_amount)
        await get_expense_category(message, state)
    else:
        await message.answer(error_text)


async def get_expense_subcategory(message: Message, state: FSMContext):
    """
    Generates subcategory keyboard and sends it to user.
    :param message: User message.
    :param state: FSM context.
    :return: Message with inline keyboard.
    """
    await state.set_state(NewExpenseStates.get_subcategory)
    state_data = await state.get_data()
    category_id = state_data['category']
    subcategories = await db.expense_operations.get_expense_subcategories(category_id)
    subcategories_keyboard = InlineKeyboardBuilder()
    title_column = 'title_ru' if message.from_user.language_code == 'ru' else 'title_en'
    for sub in subcategories:
        button = InlineKeyboardButton(text=sub[title_column], callback_data=f'subcategory:{sub["id"]}')
        subcategories_keyboard.add(button)
    back_button = InlineKeyboardButton(text='Back to categories', callback_data='back')
    subcategories_keyboard.add(back_button)
    subcategories_keyboard.adjust(2)
    await message.answer('Chose subcategory', reply_markup=subcategories_keyboard.as_markup())


@new_record_router.callback_query(NewExpenseStates.get_category)
async def save_expense_category(callback: CallbackQuery, state: FSMContext):
    """
    Saves chosen category and redirects to get_expense_subcategory.
    :param callback: Callback query.
    :param state: FSM context.
    :return: Message.
    """
    if callback.data.startswith('category'):
        user_expense_category = int(callback.data.split(':')[1])
        await callback.message.edit_reply_markup(reply_markup=None)
        await state.update_data(category=user_expense_category)
        await get_expense_subcategory(callback.message, state)
    else:
        await callback.message.answer('Choose correct category')


async def get_expense_datetime(message: Message, state: FSMContext):
    """
    Sets state to NewExpenseStates.get_datetime_amount and asks for datetime input.
    :param message: User message.
    :param state: FSM context.
    :return: Message with 'now' button.
    """
    now_keyboard = InlineKeyboardBuilder()
    now_keyboard.add(InlineKeyboardButton(text='Now', callback_data='now'))
    await state.set_state(NewExpenseStates.get_datetime)
    await message.answer('Send datetime in format like 01.12.2023 23:15', reply_markup=now_keyboard.as_markup())


@new_record_router.callback_query(NewExpenseStates.get_subcategory)
async def save_expense_subcategory(callback: CallbackQuery, state: FSMContext):
    """
    Gets callback data from subcategory keyboard. If 'back' button is pushed,
    sets state to NewExpenseStates.get_category and redirects back to get_expense_category.
    Otherwise, tries to save subcategory_id and redirects to get_expense_datetime.
    :param callback: Callback query.
    :param state: FSM context.
    :return: Message.
    """
    await callback.message.edit_reply_markup(reply_markup=None)
    if callback.data == 'back':
        await state.set_state(NewExpenseStates.get_category)
        await get_expense_category(callback.message, state)
    elif callback.data.startswith('subcategory'):
        subcategory_id = int(callback.data.split(':')[1])
        await state.update_data(subcategory=subcategory_id)
        await get_expense_datetime(callback.message, state)
    else:
        await callback.message.answer('Choose correct subcategory')


async def get_expense_location(message: Message, state: FSMContext):
    """
    Sets NewExpenseStates.get_location state and asks for location. Message contains skip button.
    :param message: User message.
    :param state: FSM context.
    :return: Message.
    """
    await state.set_state(NewExpenseStates.get_location)
    skip_keyboard = InlineKeyboardBuilder()
    skip_keyboard.add(InlineKeyboardButton(text='Skip', callback_data='no_location'))
    await message.answer('Send location', reply_markup=skip_keyboard.as_markup())


@new_record_router.callback_query(NewExpenseStates.get_datetime)
async def save_expense_datetime_from_button(callback: CallbackQuery, state: FSMContext):
    """
    Saves current datetime as expense event datetime value and redirects to get_expense_location.
    :param callback: Callback query.
    :param state: FSM context.
    :return: Message.
    """
    await callback.message.edit_reply_markup(reply_markup=None)
    if callback.data == 'now':
        await state.update_data(event_datetime=dt.datetime.now())
        await get_expense_location(callback.message, state)
    else:
        await get_expense_datetime(callback.message, state)


@new_record_router.message(NewExpenseStates.get_datetime)
async def save_expense_datetime_from_message(message: Message, state: FSMContext, bot: Bot):
    """
    If user message contains datetime, saves data and switches to get_expense_location.
    :param message: User message text.
    :param state: FSM context.
    :return: Message.
    """
    try:
        # Remove reply markup anyway
        await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.message_id - 1,
                                            reply_markup=None)
    except TelegramBadRequest:
        pass

    event_datetime, error_text = check_input.event_datetime_from_user_message(message.text)
    if event_datetime is not None:
        await state.update_data(event_datetime=event_datetime)
        await get_expense_location(message, state)
    else:
        await message.answer(error_text)


async def save_expense_data(message: Message, state: FSMContext):
    """
    Saves current state data as expense into DB and closes the process.
    :param message: User message.
    :param state: FSM context.
    :param user_table: User table name.
    :return: Message.
    """
    total_data = await state.get_data()
    try:
        await db.expense_operations.add_expense(
            user_id=total_data['user_id'],
            amount=total_data['amount'],
            subcategory_id=total_data['subcategory'],
            event_time=total_data['event_datetime'],
            location=total_data['location']
        )

        await message.answer('Saved')
    except Exception as e:
        await message.answer('Failed to save data, please try again later.')
    await state.clear()


@new_record_router.callback_query(NewExpenseStates.get_location)
async def skip_expense_location(callback: CallbackQuery, state: FSMContext):
    """
    Sets event location to None and redirects to save_expense_data.
    :param callback: Callback query.
    :param state: FSM context.
    :return: Message.
    """
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.update_data(location=None)
    await save_expense_data(callback.message, state)


@new_record_router.message(NewExpenseStates.get_location)
async def save_expense_location(message: Message, state: FSMContext, bot: Bot):
    """
    If message contains location, saves it. Otherwise, asks again.
    :param message: User message.
    :param state: FSM context.
    :param bot: Bot instance.
    :return: Message.
    """
    try:
        await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.message_id - 1, reply_markup=None)
    except TelegramBadRequest:
        pass

    if message.location is not None:
        geometry_point = check_input.tg_location_to_geometry(message.location)
        await state.update_data(location=geometry_point)
        await save_expense_data(message, state)
    else:
        await get_expense_location(message, state)


"""
============ New income ============
"""


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
    await state.update_data({'user_id': message.from_user.id})
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
async def save_income_money_amount(message: Message, state: FSMContext):
    """
    Checks if money amount from user message can be converted into positive number. If so,
    saves the value to state data and redirects to get_income_active_status. Otherwise,
    asks for correct money amount.
    :param message: User message.
    :param state: FSM context.
    :return: Message.
    """
    raw_money_amount = message.text.strip()
    money_amount, error_text = check_input.money_amount_from_user_message(raw_money_amount)
    if money_amount is not None:
        await state.update_data({'amount': money_amount})
        await get_income_active_status(message, state)
    else:
        await message.answer(error_text)


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
    try:
        await db.income_operations.add_income(
            user_id=total_data['user_id'],
            amount=total_data['amount'],
            passive=total_data['passive'],
            event_date=total_data['event_date']
        )
        await message.answer('Income data saved successfully.')
    except Exception as e:
        await message.answer('Failed to save data, please try again later.')
    await state.clear()


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
    # Remove 'today' button anyway
    try:
        await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.message_id - 1, reply_markup=None)
    except TelegramBadRequest:
        pass

    raw_event_date = message.text.strip()
    event_date, error_text = check_input.event_date_from_user_message(raw_event_date)
    if event_date is not None:
        await state.update_data({'event_date': event_date})
        # Save collected data to db
        await save_income_data_to_db(message, state)
    else:
        await message.answer(error_text)

"""
============ New expense limit ============
"""