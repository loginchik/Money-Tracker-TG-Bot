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
import db.expense_limit_operations

from bot.filters.user_exists import UserExists

from bot.states.registration import RegistrationStates
from bot.states.new_income import NewIncomeStates
from bot.states.new_expense import NewExpenseStates
from bot.states.new_expense_limit import NewExpenseLimitStates

from bot.internal import check_input
from bot.keyboards.categories_keyboard import generate_categories_keyboard
from bot.keyboards.subcategories_keyboard import generate_subcategories_keyboard
from bot.keyboards.limit_period_keyboard import generate_period_keyboard
from bot.keyboards.today_keyboard import generate_today_keyboard, generate_now_keyboard
from bot.keyboards.skip_keyboard import generate_skip_keyboard
from bot.keyboards.bool_keyboard import generate_bool_keyboard

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
@new_record_router.message(Command(commands=['add_expense_limit']), ~UserExists(), StateFilter(None))
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
    categories_keyboard = await generate_categories_keyboard(message.from_user.language_code)
    await state.set_state(NewExpenseStates.get_category)
    await message.answer('Chose category', reply_markup=categories_keyboard)


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
    subcategories_keyboard = await generate_subcategories_keyboard(category_id, message.from_user.language_code)
    await message.answer('Chose subcategory', reply_markup=subcategories_keyboard)


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
    now_keyboard = await generate_now_keyboard(message.from_user.language_code)
    await state.set_state(NewExpenseStates.get_datetime)
    await message.answer('Send datetime in format like 01.12.2023 23:15', reply_markup=now_keyboard)


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
    skip_keyboard = await generate_skip_keyboard('no_location', message.from_user.language_code)
    await message.answer('Send location', reply_markup=skip_keyboard)


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
    :return: Message.
    """
    total_data = await state.get_data()
    status = await db.expense_operations.add_expense(
            user_id=total_data['user_id'],
            amount=total_data['amount'],
            subcategory_id=total_data['subcategory'],
            event_time=total_data['event_datetime'],
            location=total_data['location']
        )
    message_text = 'Saved' if status else 'Failed to save data, please try again later.'
    await message.answer(message_text)
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
    today_markup = await generate_today_keyboard(message.from_user.language_code)
    await message.answer('Event date like 01.12.2024', reply_markup=today_markup)


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
    status = await db.income_operations.add_income(
        user_id=total_data['user_id'],
        amount=total_data['amount'],
        passive=total_data['passive'],
        event_date=total_data['event_date']
    )
    message_text = 'Income data saved successfully.' if status else 'Failed to save data, please try again later.'
    await message.answer(message_text)
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


@new_record_router.message(Command(commands='add_expense_limit'), UserExists(), StateFilter(None))
async def get_expense_limit_title(message: Message, state: FSMContext):
    await state.set_state(NewExpenseLimitStates.get_title)
    await state.update_data(user_id=message.from_user.id)
    await message.answer('Title? Length in range 1-100')


async def get_expense_limit_category(message: Message, state: FSMContext):
    await state.set_state(NewExpenseLimitStates.get_category)
    categories_keyboard = await generate_categories_keyboard(user_language_code=message.from_user.language_code)
    await message.answer('Category?', reply_markup=categories_keyboard)


@new_record_router.message(NewExpenseLimitStates.get_title)
async def save_expense_limit_title(message: Message, state: FSMContext):
    user_title = message.text.strip()
    if len(user_title) in range(1, 101):
        await state.update_data(title=message.text.strip())
        await get_expense_limit_category(message, state)
    else:
        await get_expense_limit_title(message, state)


async def get_expense_limit_subcategory(message: Message, state: FSMContext):
    state_data = await state.get_data()
    category_id = state_data['category']
    subcategories_keyboard = await generate_subcategories_keyboard(category_id, message.from_user.language_code)
    await state.set_state(NewExpenseLimitStates.get_subcategory)
    await message.answer('Subcategory?', reply_markup=subcategories_keyboard)


@new_record_router.callback_query(NewExpenseStates.get_category)
async def save_expense_limit_category(callback: CallbackQuery, state: FSMContext):
    # Remove markup anyway
    await callback.message.edit_reply_markup(reply_markup=None)
    if callback.data.startswith('category'):
        category_id = int(callback.data.split(':')[-1])
        await state.update_data(category=category_id)
        await get_expense_limit_subcategory(callback.message, state)
    else:
        await get_expense_limit_category(callback.message, state)


async def get_expense_limit_period(message: Message, state: FSMContext):
    await state.set_state(NewExpenseLimitStates.get_period)
    period_keyboard = await generate_period_keyboard(message.from_user.language_code)
    await message.answer('Period?', reply_markup=period_keyboard)


@new_record_router.callback_query(NewExpenseLimitStates.get_subcategory)
async def save_expense_limit_subcategory(callback: CallbackQuery, state: FSMContext):
    # Remove markup anyway
    await callback.message.edit_reply_markup(reply_markup=None)
    if callback.data.startswith('subcategory'):
        subcategory_id = int(callback.data.split(':')[-1])
        await state.update_data(subcategory=subcategory_id)
        await get_expense_limit_period(callback.message, state)
    # Back to list of categories
    elif callback.data == 'back':
        await get_expense_limit_category(callback.message, state)
    else:
        await get_expense_limit_subcategory(callback.message, state)


async def get_expense_limit_current_period_start(message: Message, state: FSMContext):
    await state.set_state(NewExpenseLimitStates.get_current_period_start)
    today_keyboard = await generate_today_keyboard(message.from_user.language_code)
    await message.answer('Period start?', reply_markup=today_keyboard)


@new_record_router.callback_query(NewExpenseLimitStates.get_period)
async def save_expense_limit_period(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    if callback.data.startswith('period'):
        period_id = int(callback.data.split(':')[-1])
        await state.update_data(period=period_id)
        await get_expense_limit_current_period_start(callback.message, state)
    else:
        await get_expense_limit_period(callback.message, state)


async def get_expense_limit_value(message: Message, state: FSMContext):
    await state.set_state(NewExpenseLimitStates.get_limit_value)
    await message.answer('Limit value?')


@new_record_router.callback_query(NewExpenseLimitStates.get_current_period_start)
async def save_expense_limit_period_start_from_button(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    if callback.data == 'today':
        await state.update_data(period_start=dt.datetime.today())
        await get_expense_limit_value(callback.message, state)
    else:
        await get_expense_limit_current_period_start(callback.message, state)


@new_record_router.message(NewExpenseLimitStates.get_current_period_start)
async def save_expense_limit_period_start_from_message(message: Message, state: FSMContext, bot: Bot):
    try:
        await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.message_id - 1, reply_markup=None)
    except TelegramBadRequest:
        pass

    period_start_date, error_text = check_input.event_date_from_user_message(message.text.strip())
    if period_start_date is not None:
        await state.update_data(period_start=period_start_date)
        await get_expense_limit_value(message, state)
    else:
        await message.answer(error_text)


async def get_expense_limit_end_date(message: Message, state: FSMContext):
    await state.set_state(NewExpenseLimitStates.get_end_date)
    skip_keyboard = await generate_skip_keyboard('no_end', message.from_user.language_code)
    await message.answer('End date?', reply_markup=skip_keyboard)


@new_record_router.message(NewExpenseLimitStates.get_limit_value)
async def save_expense_limit_value(message: Message, state: FSMContext):
    amount, error_text = check_input.money_amount_from_user_message(message.text.strip())
    if amount is not None:
        await state.update_data(limit_amount=amount)
        await get_expense_limit_end_date(message, state)
    else:
        await message.answer(error_text)


async def get_expense_limit_cumulative_status(message: Message, state: FSMContext):
    await state.set_state(NewExpenseLimitStates.get_cumulative)
    keyboard = await generate_bool_keyboard(message.from_user.language_code)
    await message.answer('Cumulative status?', reply_markup=keyboard)


@new_record_router.callback_query(NewExpenseLimitStates.get_end_date)
async def skip_expense_limit_end_date(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    if callback.data == 'no_end':
        await state.update_data(end_date=None)
        await get_expense_limit_cumulative_status(callback.message, state)


@new_record_router.message(NewExpenseLimitStates.get_end_date)
async def save_expense_limit_end_date(message: Message, state: FSMContext, bot: Bot):
    try:
        await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.message_id - 1, reply_markup=None)
    except TelegramBadRequest:
        pass

    end_date, error_text = check_input.event_date_from_user_message(message.text, past=False)
    if end_date is not None:
        await state.update_data(end_date=end_date)
        await get_expense_limit_cumulative_status(message, state)
    else:
        await message.answer(error_text)


async def save_expense_limit_data(message: Message, state: FSMContext):
    total_data = await state.get_data()
    status = db.expense_limit_operations.add_expense_limit(
        user_id=total_data['user_id'],
        period=total_data['period'],
        current_period_start=total_data['period_start'],
        limit_value=total_data['limit_amount'],
        cumulative=total_data['cumulative'],
        user_title=total_data['title'],
        subcategory_id=total_data['subcategory'],
        end_date=total_data['end_date']
    )
    message_text = 'Created' if status else 'Try again later'
    await message.answer(message_text)
    await state.clear()


@new_record_router.callback_query(NewExpenseLimitStates.get_cumulative)
async def save_expense_limit_cumulative_status(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    cumulative_status = callback.data == 'yes'
    await state.update_data(cumulative=cumulative_status)
    await save_expense_limit_data(callback.message, state)
