"""
Package contains scripts to add new records to db from user data. Package runs on its own router - ``new_record_router``
which must be included into main router or any other included into main router to be able to get and handle
pending updates.

First section is dedicated to `new expense record`, the main functionality of the bot. Second section is dedicated
to `income record creation`. Third section is dedicated to `create expense limit records`. All sections are handled
by ``new_record_router``.
"""

import asyncio
import datetime as dt
import logging

from aiogram import Router, Bot
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

import db.user_operations
import db.income_operations
import db.expense_operations
import db.expense_limit_operations

from bot.filters.user_exists import UserExists
from bot.middleware.user_language import UserLanguageMiddleware

from bot.states.registration import RegistrationStates
from bot.states.new_income import NewIncomeStates
from bot.states.new_expense import NewExpenseStates
from bot.states.new_expense_limit import NewExpenseLimitStates
from bot.states.export_data import ExportStates

from bot.internal import check_input
from bot.keyboards.categories_keyboard import generate_categories_keyboard
from bot.keyboards.subcategories_keyboard import generate_subcategories_keyboard
from bot.keyboards.limit_period_keyboard import generate_period_keyboard
from bot.keyboards.today_keyboard import generate_today_keyboard, generate_now_keyboard
from bot.keyboards.skip_keyboard import generate_skip_keyboard
from bot.keyboards.bool_keyboard import generate_bool_keyboard
from bot.keyboards.period_start_keyboard import generate_period_start_keyboard
from bot.keyboards.registration_keyboard import generate_registration_keyboard, generate_preferred_lang_keyboard
from bot.static.messages import NEW_ROUTER_MESSAGES

# Router to handle new records creation process
new_record_router = Router()
new_record_router.message.middleware(UserLanguageMiddleware())
new_record_router.callback_query.middleware(UserLanguageMiddleware())


"""
============ Abort the process ============
"""


@new_record_router.message(Command(commands=['abort']), ~StateFilter(None), ~StateFilter(ExportStates))
async def abort_process(message: Message, state: FSMContext, user_lang: str):
    """
    If any state is set, aborts the process and clears the state.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        message_text = NEW_ROUTER_MESSAGES['aborted'][user_lang]
        return await message.answer(message_text)


@new_record_router.message(Command(commands=['abort']), StateFilter(None))
async def no_abort(message: Message, state: FSMContext, user_lang: str):
    message_text = NEW_ROUTER_MESSAGES['nothing_to_abort'][user_lang]
    await message.answer(message_text)


@new_record_router.message(Command(commands=['abort']), StateFilter(ExportStates))
async def impossible_to_abort(message: Message, state: FSMContext, user_lang: str):
    message_text = NEW_ROUTER_MESSAGES['impossible_to_abort'][user_lang]
    await message.answer(message_text)


"""
============ User registration ============
"""


# If user is not registered, one is asked to register first
@new_record_router.message(Command(commands=['add_expense', 'add_income', 'add_expense_limit']),
                           ~UserExists(), StateFilter(None))
async def user_registration_init(message: Message, state: FSMContext):
    """
    As fas as user is not registered, one gets notified and asked if they want to register.
    Sets RegistrationStates.preferred_language state and asks user to choose the language.

    :param message: Message from user, containing command.
    :param state: FSM context to set state.
    :return: Message with inline keyboard to select one of supported languages. Message text is multilingual.
    """
    # Construct reply markup
    lang_keyboard = await generate_preferred_lang_keyboard()
    await state.set_state(RegistrationStates.preferred_language)
    await state.set_data({'command': message.text})
    # Construct message text
    message_text = ' // '.join(list(NEW_ROUTER_MESSAGES['preferred_language'].values()))
    return await message.answer(message_text, reply_markup=lang_keyboard)


async def get_registration_agreement(message: Message, state: FSMContext, user_lang: str):
    """
    Sets RegistrationStates.decision state and asks if user wants to register in database.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language from answer on previous callback query.
    :return: Message with inline keyboard.
    """
    reply_inline_keyboard = await generate_registration_keyboard(user_lang)
    await state.set_state(RegistrationStates.decision)
    message_text = NEW_ROUTER_MESSAGES['registration_agreement'][user_lang]
    return await message.answer(message_text, reply_markup=reply_inline_keyboard)


@new_record_router.callback_query(RegistrationStates.preferred_language)
async def save_language_preference(callback: CallbackQuery, state: FSMContext):
    """
    Gets user choice for preferred language and saves it into state data. Redirects
    to get_registration_agreement.
    :param callback: Callback query.
    :param state: FSM context.
    :return: Message.
    """
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.update_data(lang=callback.data)
    return await get_registration_agreement(callback.message, state, callback.data)


@new_record_router.callback_query(RegistrationStates.decision)
async def user_registration_decision(callback: CallbackQuery, state: FSMContext, user_lang: str):
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

    # User registration
    if decision == 'register':
        # Gather user data to insert into DB
        state_data = await state.get_data()
        user_data = {
            'tg_id': callback.from_user.id,
            'tg_username': callback.from_user.username,
            'tg_first_name': callback.from_user.first_name,
            'lang': state_data['lang']
        }
        # Create user and notify the user
        await asyncio.sleep(.5)
        try:
            await db.user_operations.create_user(**user_data)
            notification_text = NEW_ROUTER_MESSAGES['registration_success'][state_data['lang']]
            await callback.answer(notification_text)
            message_text = NEW_ROUTER_MESSAGES['after_registration'][state_data['lang']]
            message_text = message_text.format(state_data['command'])
            return await callback.message.answer(message_text)
        except Exception as e:
            logging.error(e)
            message_text = NEW_ROUTER_MESSAGES['registration_fail'][state_data['lang']]
            return await callback.message.answer(message_text)
        finally:
            await state.clear()
    # User doesn't want to register
    elif decision == 'cancel_register':
        message_text = NEW_ROUTER_MESSAGES['registration_cancel'][user_lang]
        await state.clear()
        return await callback.message.answer(message_text)


"""
============ New expense ============
"""


# If user is registered, process starts
@new_record_router.message(Command(commands=['add_expense']), UserExists(), StateFilter(None))
async def add_expense_init(message: Message, state: FSMContext, user_lang: str):
    """
    Sets state to NewExpenseStates.get_money_amount and asks for money amount input.
    :param message: User message.
    :param state: FSM context.
    :return: Message.
    """
    await state.clear()
    await state.set_state(NewExpenseStates.get_money_amount)
    await state.update_data(user_id=message.from_user.id)
    message_text = NEW_ROUTER_MESSAGES['expense_money_amount'][user_lang]
    return await message.answer(message_text)


async def get_expense_category(message: Message, state: FSMContext, user_lang: str):
    """
    Generates categories inline keyboard and sends it to user.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message with inline keyboard.
    """
    categories_keyboard = await generate_categories_keyboard(user_lang)
    await state.set_state(NewExpenseStates.get_category)
    message_text = NEW_ROUTER_MESSAGES['expense_category'][user_lang]
    return await message.answer(message_text, reply_markup=categories_keyboard)


@new_record_router.message(NewExpenseStates.get_money_amount)
async def save_expense_amount(message: Message, state: FSMContext, user_lang: str):
    """
    Saves money count if its correct and redirects to get_expense_category.
    :param message: User message text.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    raw_money_count = message.text.strip()
    money_amount, error_text = check_input.money_amount_from_user_message(raw_money_count, user_lang)
    if money_amount is not None:
        await state.update_data(amount=money_amount)
        return await get_expense_category(message, state, user_lang)
    else:
        return await message.answer(error_text)


async def get_expense_subcategory(message: Message, state: FSMContext, user_lang: str):
    """
    Generates subcategory keyboard and sends it to user.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message with inline keyboard.
    """
    await state.set_state(NewExpenseStates.get_subcategory)
    state_data = await state.get_data()
    category_id = state_data['category']
    subcategories_keyboard = await generate_subcategories_keyboard(category_id, user_lang)
    message_text = NEW_ROUTER_MESSAGES['expense_subcategory'][user_lang]
    return await message.answer(message_text, reply_markup=subcategories_keyboard)


@new_record_router.callback_query(NewExpenseStates.get_category)
async def save_expense_category(callback: CallbackQuery, state: FSMContext, user_lang: str):
    """
    Saves chosen category and redirects to get_expense_subcategory.
    :param callback: Callback query.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    if callback.data.startswith('category'):
        user_expense_category = int(callback.data.split(':')[1])
        await callback.message.edit_reply_markup(reply_markup=None)
        await state.update_data(category=user_expense_category)
        return await get_expense_subcategory(callback.message, state, user_lang)
    else:
        message_text = NEW_ROUTER_MESSAGES['incorrect_category'][user_lang]
        return await callback.answer(message_text)


async def get_expense_datetime(message: Message, state: FSMContext, user_lang: str):
    """
    Sets state to NewExpenseStates.get_datetime_amount and asks for datetime input.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message with 'now' button.
    """
    now_keyboard = await generate_now_keyboard(user_lang)
    await state.set_state(NewExpenseStates.get_datetime)
    message_text = NEW_ROUTER_MESSAGES['expense_datetime'][user_lang]
    return await message.answer(message_text, reply_markup=now_keyboard)


@new_record_router.callback_query(NewExpenseStates.get_subcategory)
async def save_expense_subcategory(callback: CallbackQuery, state: FSMContext, user_lang: str):
    """
    Gets callback data from subcategory keyboard. If 'back' button is pushed,
    sets state to NewExpenseStates.get_category and redirects back to get_expense_category.
    Otherwise, tries to save subcategory_id and redirects to get_expense_datetime.
    :param callback: Callback query.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    await callback.message.edit_reply_markup(reply_markup=None)
    if callback.data == 'back':
        await state.set_state(NewExpenseStates.get_category)
        return await get_expense_category(callback.message, state, user_lang)
    elif callback.data.startswith('subcategory'):
        subcategory_id = int(callback.data.split(':')[1])
        await state.update_data(subcategory=subcategory_id)
        return await get_expense_datetime(callback.message, state, user_lang)
    else:
        message_text = NEW_ROUTER_MESSAGES['incorrect_subcategory'][user_lang]
        return await callback.answer(message_text)


async def get_expense_location(message: Message, state: FSMContext, user_lang: str):
    """
    Sets NewExpenseStates.get_location state and asks for location. Message contains skip button.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    await state.set_state(NewExpenseStates.get_location)
    skip_keyboard = await generate_skip_keyboard('no_location', user_lang)
    message_text = NEW_ROUTER_MESSAGES['expense_location'][user_lang]
    return await message.answer(message_text, reply_markup=skip_keyboard)


@new_record_router.callback_query(NewExpenseStates.get_datetime)
async def save_expense_datetime_from_button(callback: CallbackQuery, state: FSMContext, user_lang: str):
    """
    Saves current datetime as expense event datetime value and redirects to get_expense_location.
    :param callback: Callback query.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    await callback.message.edit_reply_markup(reply_markup=None)
    if callback.data == 'now':
        await state.update_data(event_datetime=dt.datetime.now())
        return await get_expense_location(callback.message, state, user_lang)
    else:
        return await get_expense_datetime(callback.message, state, user_lang)


@new_record_router.message(NewExpenseStates.get_datetime)
async def save_expense_datetime_from_message(message: Message, state: FSMContext, bot: Bot, user_lang: str):
    """
    If user message contains datetime, saves data and switches to get_expense_location.
    :param message: User message text.
    :param state: FSM context.
    :param bot: Bot instance.
    :param user_lang: User language.
    :return: Message.
    """
    # Remove reply markup anyway
    try:
        await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.message_id - 1,
                                            reply_markup=None)
    except TelegramBadRequest:
        pass

    event_datetime, error_text = check_input.event_datetime_from_user_message(message.text, user_lang)
    if event_datetime is not None:
        await state.update_data(event_datetime=event_datetime)
        return await get_expense_location(message, state, user_lang)
    else:
        return await message.answer(error_text)


async def save_expense_data(message: Message, state: FSMContext, user_lang: str):
    """
    Saves current state data as expense into DB and closes the process.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language.
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
    if status:
        message_text = NEW_ROUTER_MESSAGES['expense_saved'][user_lang]
    else:
        message_text = NEW_ROUTER_MESSAGES['expense_save_error'][user_lang]
    await state.clear()
    stats_text = await db.expense_limit_operations.subcategory_expense_limit_stats(
        subcategory_id=total_data['subcategory'], user_id=total_data['user_id'], user_lang=user_lang
    )
    if stats_text is not None:
        message_text = '\n\n'.join([message_text, stats_text])
    return await message.answer(message_text)


@new_record_router.callback_query(NewExpenseStates.get_location)
async def skip_expense_location(callback: CallbackQuery, state: FSMContext, user_lang: str):
    """
    Sets event location to None and redirects to save_expense_data.
    :param callback: Callback query.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.update_data(location=None)
    return await save_expense_data(callback.message, state, user_lang)


@new_record_router.message(NewExpenseStates.get_location)
async def save_expense_location(message: Message, state: FSMContext, bot: Bot, user_lang: str):
    """
    If message contains location, saves it. Otherwise, asks again.
    :param message: User message.
    :param state: FSM context.
    :param bot: Bot instance.
    :param user_lang: User language.
    :return: Message.
    """
    try:
        await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.message_id - 1, reply_markup=None)
    except TelegramBadRequest:
        pass

    if message.location is not None:
        geometry_point = check_input.tg_location_to_geometry(message.location)
        await state.update_data(location=geometry_point)
        return await save_expense_data(message, state, user_lang)
    else:
        return await get_expense_location(message, state, user_lang)


"""
============ New income ============
"""


# If user is registered, process starts
@new_record_router.message(Command(commands=['add_income']), UserExists(), StateFilter(None))
async def add_income_init(message: Message, state: FSMContext, user_lang: str):
    """
    Sets state to NewIncomeStates.get_money_amount and asks for money amount.
    :param message: Message from user.
    :param state: FSM context to set state.
    :param user_lang: User language.
    :return: Message.
    """
    await state.set_state(NewIncomeStates.get_money_amount)
    await state.update_data({'user_id': message.from_user.id})
    message_text = NEW_ROUTER_MESSAGES['income_amount'][user_lang]
    return await message.answer(message_text)


async def get_income_active_status(message: Message, state: FSMContext, user_lang: str):
    """
    Sets state to NewIncomeStates.get_active_status and asks for active/passive income status.
    :param message: Message from user.
    :param state: FSM context to set state.
    :param user_lang: User language.
    :return: Message with inline keyboard markup.
    """
    await state.set_state(NewIncomeStates.get_active_status)
    active_status_inline_keyboard = await generate_bool_keyboard(
        user_language_code=user_lang,
        true_labels=('Активный', 'Active', 'active'),
        false_labels=('Пассивный', 'Passive', 'passive')
    )
    message_text = NEW_ROUTER_MESSAGES['active_status'][user_lang]
    return await message.answer(message_text, reply_markup=active_status_inline_keyboard)


@new_record_router.message(NewIncomeStates.get_money_amount)
async def save_income_money_amount(message: Message, state: FSMContext, user_lang: str):
    """
    Checks if money amount from user message can be converted into positive number. If so,
    saves the value to state data and redirects to get_income_active_status. Otherwise,
    asks for correct money amount.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    raw_money_amount = message.text.strip()
    money_amount, error_text = check_input.money_amount_from_user_message(raw_money_amount, user_lang)
    if money_amount is not None:
        await state.update_data({'amount': money_amount})
        return await get_income_active_status(message, state, user_lang)
    else:
        return await message.answer(error_text)


async def get_income_date(message: Message, state: FSMContext, user_lang: str):
    """
    Asks for income date.
    :param message: Message from user.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message with 'today' button.
    """
    await state.set_state(NewIncomeStates.get_event_date)
    today_markup = await generate_today_keyboard(user_lang)
    message_text = NEW_ROUTER_MESSAGES['income_date'][user_lang]
    return await message.answer(message_text, reply_markup=today_markup)


@new_record_router.callback_query(NewIncomeStates.get_active_status)
async def save_income_active_status(callback: CallbackQuery, state: FSMContext, user_lang: str):
    """
    Converts user inline choice into boolean and redirects to get_income_date.
    :param callback: User callback choice from active/passive income status keyboard.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    await state.update_data({'passive': callback.data == 'passive'})
    await callback.message.edit_reply_markup(reply_markup=None)
    return await get_income_date(callback.message, state, user_lang)


async def save_income_data_to_db(message: Message, state: FSMContext, user_lang: str):
    """
    Saves income data to DB and finished the creation process.
    :param message: Message from user.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    total_data = await state.get_data()
    status = await db.income_operations.add_income(
        user_id=total_data['user_id'],
        amount=total_data['amount'],
        passive=total_data['passive'],
        event_date=total_data['event_date']
    )
    if status:
        message_text = NEW_ROUTER_MESSAGES['income_saved'][user_lang]
    else:
        message_text = NEW_ROUTER_MESSAGES['income_save_error'][user_lang]
    await state.clear()
    return await message.answer(message_text)


@new_record_router.callback_query(NewIncomeStates.get_event_date)
async def save_income_date_from_callback(callback: CallbackQuery, state: FSMContext, user_lang: str):
    """
    Saves today's date as event date into income data dict and redirects to get_income_date.
    Keyboard is hidden after push.
    :param callback: User push button event.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    if callback.data == 'today':
        await state.update_data({'event_date': dt.date.today()})
    await callback.message.edit_reply_markup(reply_markup=None)
    return await save_income_data_to_db(callback.message, state, user_lang)


@new_record_router.message(NewIncomeStates.get_event_date)
async def save_income_date_from_message(message: Message, state: FSMContext, bot: Bot, user_lang: str):
    """
    Tries to extract date string from user message. If successful, redirects to save_income_data_to_db.
    Otherwise, asks for correct date.

    :param message: Message from user.
    :param state: FSM context.
    :param bot: Bot instance.
    :param user_lang: User language.
    :return: Message.
    """
    # Remove 'today' button anyway
    try:
        await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.message_id - 1, reply_markup=None)
    except TelegramBadRequest:
        pass

    raw_event_date = message.text.strip()
    event_date, error_text = check_input.event_date_from_user_message(raw_event_date, user_lang)
    if event_date is not None:
        await state.update_data({'event_date': event_date})
        # Save collected data to db
        return await save_income_data_to_db(message, state, user_lang)
    else:
        return await message.answer(error_text)

"""
============ New expense limit ============
"""


@new_record_router.message(Command(commands='add_expense_limit'), UserExists(), StateFilter(None))
async def get_expense_limit_title(message: Message, state: FSMContext, user_lang: str):
    """
    Sets NewExpenseLimitStates.get_title and asks for new limit title.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    await state.set_state(NewExpenseLimitStates.get_title)
    await state.update_data(user_id=message.from_user.id)
    message_text = NEW_ROUTER_MESSAGES['expense_limit_title'][user_lang]
    exist_titles = await db.expense_limit_operations.user_expense_limits(message.from_user.id)
    if len(exist_titles) > 0:
        exist_titles_string = ', '.join(['<i>' + t + '</i>' for t in exist_titles])
        message_text += NEW_ROUTER_MESSAGES['expense_limit_existent_limits'][user_lang].format(exist_titles_string)
    return await message.answer(message_text, parse_mode=ParseMode.HTML)


async def get_expense_limit_category(message: Message, state: FSMContext, user_lang: str):
    """
    Sets NewExpenseLimitStates.get_category state and asks for new limit category.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    await state.set_state(NewExpenseLimitStates.get_category)
    categories_keyboard = await generate_categories_keyboard(user_language_code=user_lang)
    message_text = NEW_ROUTER_MESSAGES['expense_limit_category'][user_lang]
    return await message.answer(message_text, reply_markup=categories_keyboard)


@new_record_router.message(NewExpenseLimitStates.get_title)
async def save_expense_limit_title(message: Message, state: FSMContext, user_lang: str):
    """
    Saves expense limit title if it satisfies conditions and redirects to get_expense_limit_category.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    user_title = message.text.strip()
    if len(user_title) in range(1, 101):
        await state.update_data(title=message.text.strip())
        return await get_expense_limit_category(message, state, user_lang)
    else:
        message_text = NEW_ROUTER_MESSAGES['expense_limit_title_too_long'][user_lang]
        return await message.reply(message_text)


async def get_expense_limit_subcategory(message: Message, state: FSMContext, user_lang: str):
    """
    Sets NewExpenseLimitStates.get_subcategory state and asks for subcategory.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    state_data = await state.get_data()
    category_id = state_data['category']
    subcategories_keyboard = await generate_subcategories_keyboard(category_id, user_lang)
    await state.set_state(NewExpenseLimitStates.get_subcategory)
    message_text = NEW_ROUTER_MESSAGES['expense_limit_subcategory'][user_lang]
    return await message.answer(message_text, reply_markup=subcategories_keyboard)


@new_record_router.callback_query(NewExpenseLimitStates.get_category)
async def save_expense_limit_category(callback: CallbackQuery, state: FSMContext, user_lang: str):
    """
    Saves user category choice and redirects to get_expense_limit_subcategory.
    :param callback: Callback query.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    # Remove markup anyway
    await callback.message.edit_reply_markup(reply_markup=None)
    if callback.data.startswith('category'):
        category_id = int(callback.data.split(':')[-1])
        await state.update_data(category=category_id)
        return await get_expense_limit_subcategory(callback.message, state, user_lang)
    else:
        return await get_expense_limit_category(callback.message, state, user_lang)


async def get_expense_limit_period(message: Message, state: FSMContext, user_lang: str):
    """
    Sets NewExpenseLimitStates.get_period state and asks for new limit period.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    await state.set_state(NewExpenseLimitStates.get_period)
    period_keyboard = await generate_period_keyboard(user_lang)
    message_text = NEW_ROUTER_MESSAGES['expense_limit_period'][user_lang]
    return await message.answer(message_text, reply_markup=period_keyboard)


@new_record_router.callback_query(NewExpenseLimitStates.get_subcategory)
async def save_expense_limit_subcategory(callback: CallbackQuery, state: FSMContext, user_lang: str):
    """
    Saves user subcategory choice and redirects to get_expense_limit_period.
    :param callback: Callback query.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    # Remove markup anyway
    await callback.message.edit_reply_markup(reply_markup=None)
    if callback.data.startswith('subcategory'):
        subcategory_id = int(callback.data.split(':')[-1])
        await state.update_data(subcategory=subcategory_id)
        return await get_expense_limit_period(callback.message, state, user_lang)
    # Back to list of categories
    elif callback.data == 'back':
        return await get_expense_limit_category(callback.message, state, user_lang)
    else:
        return await get_expense_limit_subcategory(callback.message, state, user_lang)


async def get_expense_limit_current_period_start(message: Message, state: FSMContext, user_lang: str):
    """
    Sets NewExpenseLimitStates.get_current_period_start and asks for user input.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    await state.set_state(NewExpenseLimitStates.get_current_period_start)
    state_data = await state.get_data()
    user_period = state_data['period']
    keyboard = await generate_period_start_keyboard(user_period)
    message_text = NEW_ROUTER_MESSAGES['expense_limit_period_start'][user_lang]
    return await message.answer(message_text, reply_markup=keyboard)


@new_record_router.callback_query(NewExpenseLimitStates.get_period)
async def save_expense_limit_period(callback: CallbackQuery, state: FSMContext, user_lang: str):
    """
    Saves user period choice and redirects to get_expense_limit_current_period_start.
    :param callback: Callback query.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    await callback.message.edit_reply_markup(reply_markup=None)
    if callback.data.startswith('period'):
        period_id = int(callback.data.split(':')[-1])
        await state.update_data(period=period_id)
        return await get_expense_limit_current_period_start(callback.message, state, user_lang)
    else:
        return await get_expense_limit_period(callback.message, state, user_lang)


async def get_expense_limit_value(message: Message, state: FSMContext, user_lang: str):
    """
    Sets NewExpenseLimitStates.get_value state and asks for new limit value.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    await state.set_state(NewExpenseLimitStates.get_limit_value)
    message_text = NEW_ROUTER_MESSAGES['expense_limit_value'][user_lang]
    return await message.answer(message_text)


@new_record_router.callback_query(NewExpenseLimitStates.get_current_period_start)
async def save_expense_limit_period_start_from_button(callback: CallbackQuery, state: FSMContext, user_lang: str):
    """
    Saves user period choice and redirects to get_expense_limit_value.
    :param callback: Callback query.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    await callback.message.edit_reply_markup(reply_markup=None)
    try:
        date_from_callback = dt.datetime.strptime(callback.data, '%d.%m.%Y').date()
        await state.update_data(period_start=date_from_callback)
        return await get_expense_limit_value(callback.message, state, user_lang)
    except (ValueError, Exception) as e:
        logging.error(e)
        return await get_expense_limit_current_period_start(callback.message, state, user_lang)


@new_record_router.message(NewExpenseLimitStates.get_current_period_start)
async def save_expense_limit_period_start_from_message(message: Message, state: FSMContext, bot: Bot, user_lang: str):
    """
    Saves user period start and redirects to get_expense_limit_value.
    :param message: User message.
    :param state: FSM context.
    :param bot: Bot instance.
    :param user_lang: User language.
    :return: Message.
    """
    try:
        await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.message_id - 1, reply_markup=None)
    except TelegramBadRequest:
        pass

    period_start_date, error_text = check_input.event_date_from_user_message(message.text.strip(), user_lang)
    if period_start_date is not None:
        await state.update_data(period_start=period_start_date)
        return await get_expense_limit_value(message, state, user_lang)
    else:
        return await message.answer(error_text)


async def get_expense_limit_end_date(message: Message, state: FSMContext, user_lang: str):
    """
    Sets NewExpenseLimitStates.get_end_date state and asks for new limit value.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    await state.set_state(NewExpenseLimitStates.get_end_date)
    skip_keyboard = await generate_skip_keyboard('no_end', user_lang)
    message_text = NEW_ROUTER_MESSAGES['expense_limit_end_date'][user_lang]
    return await message.answer(message_text, reply_markup=skip_keyboard)


@new_record_router.message(NewExpenseLimitStates.get_limit_value)
async def save_expense_limit_value(message: Message, state: FSMContext, user_lang: str):
    """
    Saves user expense limit value and redirects to get_expense_limit_end_date.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    amount, error_text = check_input.money_amount_from_user_message(message.text.strip(), user_lang)
    if amount is not None:
        await state.update_data(limit_amount=amount)
        return await get_expense_limit_end_date(message, state, user_lang)
    else:
        return await message.answer(error_text)


async def get_expense_limit_cumulative_status(message: Message, state: FSMContext, user_lang: str):
    """
    Sets NewExpenseLimitStates.get_cumulative_status state and asks for user choice.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    await state.set_state(NewExpenseLimitStates.get_cumulative)
    keyboard = await generate_bool_keyboard(user_lang, true_labels=('Копить', 'Cumulative', 'true'),
                                            false_labels=('Сбрасывать', 'Reset', 'false'))
    message_text = NEW_ROUTER_MESSAGES['expense_limit_cumulative'][user_lang]
    return await message.answer(message_text, reply_markup=keyboard)


@new_record_router.callback_query(NewExpenseLimitStates.get_end_date)
async def skip_expense_limit_end_date(callback: CallbackQuery, state: FSMContext, user_lang: str):
    """
    Save expense limit end date as None and redirects to get_expense_limit_cumulative_status.
    :param callback: Callback query.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    await callback.message.edit_reply_markup(reply_markup=None)
    if callback.data == 'no_end':
        await state.update_data(end_date=None)
        return await get_expense_limit_cumulative_status(callback.message, state, user_lang)


@new_record_router.message(NewExpenseLimitStates.get_end_date)
async def save_expense_limit_end_date(message: Message, state: FSMContext, bot: Bot, user_lang: str):
    """
    Saves user entered end date and redirects to get_expense_limit_cumulative_status.
    :param message: User message.
    :param state: FSM context.
    :param bot: Bot instance.
    :param user_lang: User language.
    :return: Message.
    """
    try:
        await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.message_id - 1, reply_markup=None)
    except TelegramBadRequest:
        pass

    end_date, error_text = check_input.event_date_from_user_message(message.text, past=False, user_lang=user_lang)
    if end_date is not None:
        await state.update_data(end_date=end_date)
        return await get_expense_limit_cumulative_status(message, state, user_lang)
    else:
        return await message.answer(error_text)


async def save_expense_limit_data(message: Message, state: FSMContext, user_lang: str):
    """
    Saves user expense limit to database.
    :param message: User message.
    :param state: FSM context.
    :param user_lang: User language.
    :return:
    """
    total_data = await state.get_data()
    status = await db.expense_limit_operations.add_expense_limit(
        user_id=total_data['user_id'],
        period=total_data['period'],
        current_period_start=total_data['period_start'],
        limit_value=total_data['limit_amount'],
        cumulative=total_data['cumulative'],
        user_title=total_data['title'],
        subcategory_id=total_data['subcategory'],
        end_date=total_data['end_date']
    )
    if status:
        message_text = NEW_ROUTER_MESSAGES['expense_limit_saved'][user_lang]
    else:
        message_text = NEW_ROUTER_MESSAGES['expense_limit_save_error'][user_lang]
    await state.clear()
    return await message.answer(message_text)


@new_record_router.callback_query(NewExpenseLimitStates.get_cumulative)
async def save_expense_limit_cumulative_status(callback: CallbackQuery, state: FSMContext, user_lang: str):
    """
    Saves user cumulative choice and redirects to save_expense_limit_data.
    :param callback: Callback query.
    :param state: FSM context.
    :param user_lang: User language.
    :return: Message.
    """
    await callback.message.edit_reply_markup(reply_markup=None)
    cumulative_status = callback.data == 'true'
    await state.update_data(cumulative=cumulative_status)
    return await save_expense_limit_data(callback.message, state, user_lang)
