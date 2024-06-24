import asyncio
import datetime as dt
from loguru import logger

import asyncpg
from aiogram import Router, Bot
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from db import BotUser, Expense, ExpenseLimit, Income
from bot.filters import UserExists
from bot.fsm_states import RegistrationStates, NewIncomeStates, NewExpenseStates, NewExpenseLimitStates, ExportStates
from bot.internal import check_input
from bot.keyboards import (
    binary_keyboard, one_button_keyboard,
    categories_keyboard, subcategories_keyboard, period_keyboard
)
from bot.static.messages import NEW_ROUTER_MESSAGES


class NewRecordRouter(Router):
    def __init__(self):
        super().__init__()
        self.name = 'NewRecordRouter'
        self.register_handlers()

    def register_handlers(self):
        self.message.register(self.abort_process, Command(commands=['abort']))

        registration = RegistrationRouter()
        new_expense = NewExpenseRouter()
        new_income = NewIncomeRouter()
        new_expense_limit = NewExpenseLimitRouter()
        self.include_routers(registration, new_expense, new_income, new_expense_limit)
        logger.debug(f'Added ({registration.name}, {new_expense.name}, {new_income.name}, {new_expense_limit.name}) to {self.name}')

    @staticmethod
    async def abort_process(message, state, user_lang):
        """
        If any state is set, aborts the process and clears the state.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        current_state = await state.get_state()
        if current_state is not None:
            # Export process cannot be aborted
            if current_state in [st for st in ExportStates.__state_names__]:
                message_text = NEW_ROUTER_MESSAGES['impossible_to_abort'][user_lang]
                return await message.answer(message_text)
            # Other processes can
            else:
                await state.clear()
                message_text = NEW_ROUTER_MESSAGES['aborted'][user_lang]
                return await message.answer(message_text)
        # There is no state set
        else:
            message_text = NEW_ROUTER_MESSAGES['nothing_to_abort'][user_lang]
            return await message.answer(message_text)


class RegistrationRouter(Router):
    def __init__(self):
        super().__init__()
        self.name = 'RegistrationRouter'
        self.register_handlers()

    def register_handlers(self):
        self.message.register(self.start_registration, Command(commands=['add_expense', 'add_income', 'add_expense_limit']), ~UserExists(), StateFilter(None))
        self.callback_query.register(self.save_language_preference, RegistrationStates.preferred_language)
        self.callback_query.register(self.user_registration_decision, RegistrationStates.decision)

    @staticmethod
    async def start_registration(message: Message, state: FSMContext, user_lang: str):
        """
        As fas as user is not registered, one gets notified and asked if they want to register.
        Sets RegistrationStates.preferred_language state and asks user to choose the language.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Message with inline keyboard to select one of supported languages. Message text is multilingual.
        """
        # Construct reply markup
        lang_keyboard = binary_keyboard(user_language_code=user_lang,
                                        first_button_data=('Русский', 'Русский', 'ru'),
                                        second_button_data=('English', 'English', 'en'),
                                        )
        await state.set_state(RegistrationStates.preferred_language)
        await state.set_data({'command': message.text})
        # Construct message text
        message_text = ' // '.join(list(NEW_ROUTER_MESSAGES['preferred_language'].values()))
        return await message.answer(message_text, reply_markup=lang_keyboard)

    async def save_language_preference(self, callback: CallbackQuery, state: FSMContext):
        """
        Gets user choice for preferred language and saves it into state data. Redirects
        to get_registration_agreement.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
        """
        await callback.message.edit_reply_markup(reply_markup=None)
        await state.update_data(lang=callback.data)
        return await self.get_registration_agreement(callback.message, state, callback.data)

    @staticmethod
    async def get_registration_agreement(message: Message, state: FSMContext, user_lang: str):
        """
        Sets RegistrationStates.decision state and asks if user wants to register in database.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Message with inline keyboard.
        """
        keyboard = binary_keyboard(user_language_code=user_lang,
                                   first_button_data=('Создать аккаунт', 'Register', 'register'),
                                   second_button_data=('Отмена', 'Cancel', 'cancel_registration'))
        await state.set_state(RegistrationStates.decision)
        message_text = NEW_ROUTER_MESSAGES['registration_agreement'][user_lang]
        return await message.answer(message_text, reply_markup=keyboard)

    @staticmethod
    async def user_registration_decision(callback: CallbackQuery, state: FSMContext, user_lang, async_session):
        """
        Gets user decision in terms of registration. If user want to register, adds their data to db
        and continues initial command process. Otherwise, doesn't register the user and notifies
        about user unavailability to continue.

        Args:
            callback (CallbackQuery): Callback query from registration inline keyboard.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession object.

        Returns:
            Message:
        """
        # Get user decision from callback
        decision = callback.data
        # Remove markup from message to prevent button re-pushing
        await callback.message.edit_reply_markup(reply_markup=None)

        # User registration
        if decision == 'register':
            # Gather user data to insert into DB
            state_data = await state.get_data()
            # Create user and notify the user
            await asyncio.sleep(.5)
            try:
                await BotUser.create(tg_id=callback.from_user.id, tg_username=callback.from_user.username,
                                     tg_first_name=callback.from_user.first_name, lang=state_data['lang'],
                                     async_session=async_session)

                notification_text = NEW_ROUTER_MESSAGES['registration_success'][state_data['lang']]
                await callback.answer(notification_text)
                message_text = NEW_ROUTER_MESSAGES['after_registration'][state_data['lang']]
                message_text = message_text.format(state_data['command'])
                return await callback.message.answer(message_text)
            except (ValueError, Exception) as e:
                logger.error(e)
                message_text = NEW_ROUTER_MESSAGES['registration_fail'][state_data['lang']]
                return await callback.message.answer(message_text)
            finally:
                await state.clear()
        # User doesn't want to register
        elif decision == 'cancel_register':
            message_text = NEW_ROUTER_MESSAGES['registration_cancel'][user_lang]
            await state.clear()
            return await callback.message.answer(message_text)


class NewExpenseRouter(Router):
    def __init__(self):
        super().__init__()
        self.name = 'NewExpenseRouter'
        self.register_handlers()

    def register_handlers(self):
        self.message.register(self.add_expense_init, Command(commands=['add_expense']), UserExists(), StateFilter(None))
        self.message.register(self.save_expense_amount, NewExpenseStates.get_money_amount)
        self.callback_query.register(self.save_expense_category, NewExpenseStates.get_category)
        self.callback_query.register(self.save_expense_subcategory, NewExpenseStates.get_subcategory)
        self.callback_query.register(self.save_expense_datetime_from_button, NewExpenseStates.get_datetime)
        self.message.register(self.save_expense_datetime_from_message, NewExpenseStates.get_datetime)
        self.callback_query.register(self.skip_expense_location, NewExpenseStates.get_location)
        self.message.register(self.save_expense_location, NewExpenseStates.get_location)

    @staticmethod
    async def add_expense_init(message: Message, state: FSMContext, user_lang):
        """
        Sets state to NewExpenseStates.get_money_amount and asks for money amount input.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        await state.clear()
        await state.set_state(NewExpenseStates.get_money_amount)
        await state.update_data(user_id=message.from_user.id)
        message_text = NEW_ROUTER_MESSAGES['expense_money_amount'][user_lang]
        return await message.answer(message_text)

    async def save_expense_amount(self, message: Message, state: FSMContext, user_lang, async_session):
        """
        Saves money count if its correct and redirects to get_expense_category.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession object.

        Returns:
            Message: Reply message.
        """
        raw_money_count = message.text.strip()
        money_amount, error_text = check_input.money_amount_from_user_message(raw_money_count, user_lang)
        if money_amount is not None:
            await state.update_data(amount=money_amount)
            return await self.get_expense_category(message, state, user_lang, async_session)
        else:
            return await message.answer(error_text)

    @staticmethod
    async def get_expense_category(message: Message, state: FSMContext, user_lang, async_session):
        """
        Generates categories inline keyboard and sends it to user.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession object.

        Returns:
             Message: Message with inline keyboard.
        """
        keyboard = await categories_keyboard(user_lang, async_session)
        await state.set_state(NewExpenseStates.get_category)
        message_text = NEW_ROUTER_MESSAGES['expense_category'][user_lang]
        return await message.answer(message_text, reply_markup=keyboard)

    async def save_expense_category(self, callback: CallbackQuery, state: FSMContext, user_lang, async_session):
        """
        Saves chosen category and redirects to get_expense_subcategory.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession object.

        Returns:
            Message: Reply message.
        """
        if callback.data.startswith('category'):
            user_expense_category = int(callback.data.split(':')[1])
            await callback.message.edit_reply_markup(reply_markup=None)
            await state.update_data(category=user_expense_category)
            return await self.get_expense_subcategory(callback.message, state, user_lang, async_session)
        else:
            message_text = NEW_ROUTER_MESSAGES['incorrect_category'][user_lang]
            return await callback.answer(message_text)

    @staticmethod
    async def get_expense_subcategory(message: Message, state: FSMContext, user_lang, async_session):
        """
        Generates subcategory keyboard and sends it to user.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession object.

        Returns:
            Message: Message with inline keyboard.
        """
        await state.set_state(NewExpenseStates.get_subcategory)
        state_data = await state.get_data()
        category_id = state_data['category']
        keyboard = await subcategories_keyboard(category_id, user_lang, async_session)
        message_text = NEW_ROUTER_MESSAGES['expense_subcategory'][user_lang]
        return await message.answer(message_text, reply_markup=keyboard)

    async def save_expense_subcategory(self, callback: CallbackQuery, state: FSMContext, user_lang, async_session):
        """
        Gets callback data from subcategory keyboard. If 'back' button is pushed,
        sets state to NewExpenseStates.get_category and redirects back to get_expense_category.
        Otherwise, tries to save subcategory_id and redirects to get_expense_datetime.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession object.

        Returns:
            Message: Reply message.
        """
        await callback.message.edit_reply_markup(reply_markup=None)
        if callback.data == 'back':
            await state.set_state(NewExpenseStates.get_category)
            return await self.get_expense_category(callback.message, state, user_lang, async_session)
        elif callback.data.startswith('subcategory'):
            subcategory_id = int(callback.data.split(':')[1])
            await state.update_data(subcategory=subcategory_id)
            return await self.get_expense_datetime(callback.message, state, user_lang)
        else:
            message_text = NEW_ROUTER_MESSAGES['incorrect_subcategory'][user_lang]
            return await callback.answer(message_text)

    @staticmethod
    async def get_expense_datetime(message: Message, state: FSMContext, user_lang):
        """
        Sets state to NewExpenseStates.get_datetime_amount and asks for datetime input.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Message with 'now' button.
        """
        keyboard = one_button_keyboard(user_language=user_lang, labels=('Сейчас', 'Now'), callback_data='now')
        await state.set_state(NewExpenseStates.get_datetime)
        message_text = NEW_ROUTER_MESSAGES['expense_datetime'][user_lang]
        return await message.answer(message_text, reply_markup=keyboard)

    async def save_expense_datetime_from_button(self, callback: CallbackQuery, state: FSMContext, user_lang):
        """
        Saves current datetime as expense event datetime value and redirects to get_expense_location.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        await callback.message.edit_reply_markup(reply_markup=None)
        if callback.data == 'now':
            await state.update_data(event_datetime=dt.datetime.now())
            return await self.get_expense_location(callback.message, state, user_lang)
        else:
            return await self.get_expense_datetime(callback.message, state, user_lang)

    async def save_expense_datetime_from_message(self, message: Message, state: FSMContext, bot, user_lang):
        """
        If user message contains datetime, saves data and switches to get_expense_location.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            bot (Bot): Bot instance.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        # Remove reply markup anyway
        try:
            await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.message_id - 1, reply_markup=None)
        except TelegramBadRequest:
            pass

        event_datetime, error_text = check_input.event_datetime_from_user_message(message.text, user_lang)
        if event_datetime is not None:
            await state.update_data(event_datetime=event_datetime)
            return await self.get_expense_location(message, state, user_lang)
        else:
            return await message.answer(error_text)

    @staticmethod
    async def get_expense_location(message: Message, state: FSMContext, user_lang: str):
        """
        Sets NewExpenseStates.get_location state and asks for location. Message contains skip button.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        keyboard = one_button_keyboard(labels=('Пропустить', 'Skip'), callback_data='no_location', user_language=user_lang)
        await state.set_state(NewExpenseStates.get_location)
        message_text = NEW_ROUTER_MESSAGES['expense_location'][user_lang]
        return await message.answer(message_text, reply_markup=keyboard)

    async def save_expense_location(self, message, state, bot, user_lang, async_session):
        """
        If message contains location, saves it. Otherwise, asks again.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            bot (Bot): Bot instance.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession object.

        Returns:
            Message: Reply message.
        """
        try:
            await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.message_id - 1,
                                                reply_markup=None)
        except TelegramBadRequest:
            pass

        if message.location is not None:
            geometry_point = check_input.tg_location_to_geometry(message.location)
            await state.update_data(location=geometry_point)
            return await self.save_expense_data(message, state, user_lang, async_session)
        else:
            return await self.get_expense_location(message, state, user_lang)

    async def skip_expense_location(self, callback: CallbackQuery, state: FSMContext, user_lang, async_session):
        """
        Sets event location to None and redirects to save_expense_data.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession object.
        Returns:
             Message: Reply message.
        """
        await callback.message.edit_reply_markup(reply_markup=None)
        await state.update_data(location=None)
        return await self.save_expense_data(callback.message, state, user_lang, async_session)

    @staticmethod
    async def save_expense_data(message: Message, state: FSMContext, user_lang: str, async_session):
        """
        Saves current state data as expense into DB and closes the process.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession object.

        Returns:
            Message: Reply message.
        """
        total_data = await state.get_data()
        try:
            await Expense.create(user_id=total_data['user_id'], amount=total_data['amount'],
                                 subcategory_id=total_data['subcategory'], event_time=total_data['event_datetime'],
                                 location=total_data['location'], async_session=async_session)
            message_text = NEW_ROUTER_MESSAGES['expense_saved'][user_lang]
            return await message.answer(message_text)

        except (ValueError, Exception) as e:
            logger.error(e)
            message_text = NEW_ROUTER_MESSAGES['expense_save_error'][user_lang]
            return await message.answer(message_text)
        finally:
            await state.clear()


class NewIncomeRouter(Router):
    def __init__(self):
        super().__init__()
        self.name = 'NewIncomeRouter'
        self.register_handlers()

    def register_handlers(self):
        self.message.register(self.add_income_init, Command(commands=['add_income']), UserExists(), StateFilter(None))
        self.message.register(self.save_income_money_amount, NewIncomeStates.get_money_amount)
        self.callback_query.register(self.save_income_active_status, NewIncomeStates.get_active_status)
        self.callback_query.register(self.save_income_date_from_callback, NewIncomeStates.get_event_date)
        self.message.register(self.save_income_date_from_message, NewIncomeStates.get_event_date)

    @staticmethod
    async def add_income_init(message, state, user_lang):
        """
        Sets state to NewIncomeStates.get_money_amount and asks for money amount.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        await state.set_state(NewIncomeStates.get_money_amount)
        await state.update_data({'user_id': message.from_user.id})
        message_text = NEW_ROUTER_MESSAGES['income_amount'][user_lang]
        return await message.answer(message_text)

    async def save_income_money_amount(self, message, state, user_lang):
        """
        Checks if money amount from user message can be converted into positive number. If so,
        saves the value to state data and redirects to get_income_active_status. Otherwise,
        asks for correct money amount.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        raw_money_amount = message.text.strip()
        money_amount, error_text = check_input.money_amount_from_user_message(raw_money_amount, user_lang)
        if money_amount is not None:
            await state.update_data({'amount': money_amount})
            return await self.get_income_active_status(message, state, user_lang)
        else:
            return await message.answer(error_text)

    @staticmethod
    async def get_income_active_status(message, state, user_lang):
        """
        Sets state to NewIncomeStates.get_active_status and asks for active/passive income status.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        await state.set_state(NewIncomeStates.get_active_status)
        keyboard = binary_keyboard(
            user_language_code=user_lang,
            first_button_data=('Активный', 'Active', 'active'),
            second_button_data=('Пассивный', 'Passive', 'passive')
        )
        message_text = NEW_ROUTER_MESSAGES['active_status'][user_lang]
        return await message.answer(message_text, reply_markup=keyboard)

    async def save_income_active_status(self, callback: CallbackQuery, state: FSMContext, user_lang: str):
        """
        Converts user inline choice into boolean and redirects to get_income_date.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        await state.update_data({'passive': callback.data == 'passive'})
        await callback.message.edit_reply_markup(reply_markup=None)
        return await self.get_income_date(callback.message, state, user_lang)

    @staticmethod
    async def get_income_date(message: Message, state: FSMContext, user_lang: str):
        """
        Asks for income date.
        :param message: Message from user.
        :param state: FSM context.
        :param user_lang: User language.
        :return: Message with 'today' button.
        """
        await state.set_state(NewIncomeStates.get_event_date)
        today_markup = one_button_keyboard(labels=('Сегодня', 'Today'), callback_data='today', user_language=user_lang)
        message_text = NEW_ROUTER_MESSAGES['income_date'][user_lang]
        return await message.answer(message_text, reply_markup=today_markup)

    async def save_income_date_from_callback(self, callback, state, user_lang, async_session):
        """
        Saves today's date as event date into income data dict and redirects to get_income_date.
        Keyboard is hidden after push.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (AsyncSession): AsyncSession object.

        Returns:
            Message: Reply message.
        """
        if callback.data == 'today':
            await state.update_data({'event_date': dt.date.today()})
        await callback.message.edit_reply_markup(reply_markup=None)
        return await self.save_income_data_to_db(callback.message, state, user_lang, async_session)

    # @new_record_router.message(NewIncomeStates.get_event_date)
    async def save_income_date_from_message(self, message: Message, state: FSMContext, bot: Bot, user_lang, async_session):
        """
        Tries to extract date string from user message. If successful, redirects to save_income_data_to_db.
        Otherwise, asks for correct date.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (AsyncSession): AsyncSession object.
            bot (Bot): Bot object.

        Returns:
            Message: Reply message.
        """
        # Remove 'today' button anyway
        try:
            await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.message_id - 1,
                                                reply_markup=None)
        except TelegramBadRequest:
            pass

        raw_event_date = message.text.strip()
        event_date, error_text = check_input.event_date_from_user_message(raw_event_date, user_lang)
        if event_date is not None:
            await state.update_data({'event_date': event_date})
            # Save collected data to db
            return await self.save_income_data_to_db(message, state, user_lang, async_session)
        else:
            return await message.answer(error_text)

    @staticmethod
    async def save_income_data_to_db(message: Message, state: FSMContext, user_lang: str, async_session):
        """
        Saves income data to DB and finished the creation process.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (AsyncSession): AsyncSession object.

        Returns:
            Message: Reply message.
        """
        total_data = await state.get_data()
        try:
            await Income.create(user_id=total_data['user_id'], amount=total_data['amount'],
                                passive=total_data['passive'], event_date=total_data['event_date'],
                                async_session=async_session)
            message_text = NEW_ROUTER_MESSAGES['income_saved'][user_lang]
            return await message.answer(message_text)

        except (ValueError, Exception) as e:
            logger.error(e)
            message_text = NEW_ROUTER_MESSAGES['income_save_error'][user_lang]
            return await message.answer(message_text)

        finally:
            await state.clear()


class NewExpenseLimitRouter(Router):
    def __init__(self):
        super().__init__()
        self.name = 'NewExpenseLimitRouter'
        self.register_handlers()

    def register_handlers(self):
        self.message.register(self.get_expense_limit_title, Command(commands='add_expense_limit'), UserExists(), StateFilter(None))

        self.message.register(self.save_expense_limit_title, NewExpenseLimitStates.get_title)

        self.callback_query.register(self.save_expense_limit_category, NewExpenseLimitStates.get_category)

        self.callback_query.register(self.save_expense_limit_subcategory, NewExpenseLimitStates.get_subcategory)

        self.callback_query.register(self.save_expense_limit_period, NewExpenseLimitStates.get_period)

        self.callback_query.register(self.save_expense_limit_period_start_from_button, NewExpenseLimitStates.get_current_period_start)
        self.message.register(self.save_expense_limit_period_start_from_message, NewExpenseLimitStates.get_current_period_start)

        self.message.register(self.save_expense_limit_value, NewExpenseLimitStates.get_limit_value)

        self.message.register(self.save_expense_limit_end_date, NewExpenseLimitStates.get_end_date)
        self.callback_query.register(self.skip_expense_limit_end_date, NewExpenseLimitStates.get_end_date)

        self.callback_query.register(self.save_expense_limit_cumulative_status, NewExpenseLimitStates.get_cumulative)

    @staticmethod
    async def get_expense_limit_title(message: Message, state: FSMContext, user_lang: str, async_session):
        """
        Sets NewExpenseLimitStates.get_title and asks for new limit title.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession object.

        Returns:
            Message: Reply message.
        """
        await state.set_state(NewExpenseLimitStates.get_title)
        await state.update_data(user_id=message.from_user.id)
        message_text = NEW_ROUTER_MESSAGES['expense_limit_title'][user_lang]
        exist = await ExpenseLimit.select_by_user_id(user_id=message.from_user.id, async_session=async_session)
        exist_titles = [ex.user_title for ex in exist]
        if len(exist_titles) > 0:
            exist_titles_string = ', '.join(['<i>' + t + '</i>' for t in exist_titles])
            message_text += NEW_ROUTER_MESSAGES['expense_limit_existent_limits'][user_lang].format(exist_titles_string)
        return await message.answer(message_text, parse_mode=ParseMode.HTML)

    async def save_expense_limit_title(self, message: Message, state: FSMContext, user_lang: str, async_session):
        """
        Saves expense limit title if it satisfies conditions and redirects to get_expense_limit_category.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession object.

        Returns:
            Message: Reply message.
        """
        user_title = message.text.strip()
        if len(user_title) in range(1, 101):
            await state.update_data(title=message.text.strip())
            return await self.get_expense_limit_category(message, state, user_lang, async_session)
        else:
            message_text = NEW_ROUTER_MESSAGES['expense_limit_title_too_long'][user_lang]
            return await message.reply(message_text)

    @staticmethod
    async def get_expense_limit_category(message: Message, state: FSMContext, user_lang: str, async_session):
        """
        Sets NewExpenseLimitStates.get_category state and asks for new limit category.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession object.

        Returns:
            Message: Reply message.
        """
        await state.set_state(NewExpenseLimitStates.get_category)
        keyboard = await categories_keyboard(user_language_code=user_lang, async_session=async_session)
        message_text = NEW_ROUTER_MESSAGES['expense_limit_category'][user_lang]
        return await message.answer(message_text, reply_markup=keyboard)

    async def save_expense_limit_category(self, callback: CallbackQuery, state: FSMContext, user_lang, async_session):
        """
        Saves user category choice and redirects to get_expense_limit_subcategory.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession object.

        Returns:
            Message: Reply message.
        """
        # Remove markup anyway
        await callback.message.edit_reply_markup(reply_markup=None)
        if callback.data.startswith('category'):
            category_id = int(callback.data.split(':')[-1])
            await state.update_data(category=category_id)
            return await self.get_expense_limit_subcategory(callback.message, state, user_lang, async_session)
        else:
            return await self.get_expense_limit_category(callback.message, state, user_lang, async_session)

    @staticmethod
    async def get_expense_limit_subcategory(message: Message, state: FSMContext, user_lang, async_session):
        """
        Sets NewExpenseLimitStates.get_subcategory state and asks for subcategory.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession object.

        Returns:
            Message: Reply message.
        """
        state_data = await state.get_data()
        category_id = state_data['category']
        keyboard = await subcategories_keyboard(category_id, user_lang, async_session)
        await state.set_state(NewExpenseLimitStates.get_subcategory)
        message_text = NEW_ROUTER_MESSAGES['expense_limit_subcategory'][user_lang]
        return await message.answer(message_text, reply_markup=keyboard)

    async def save_expense_limit_subcategory(self, callback: CallbackQuery, state: FSMContext, user_lang, async_session):
        """
        Saves user subcategory choice and redirects to get_expense_limit_period.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession object.

        Returns:
            Message: Reply message.
        """
        # Remove markup anyway
        await callback.message.edit_reply_markup(reply_markup=None)
        if callback.data.startswith('subcategory'):
            subcategory_id = int(callback.data.split(':')[-1])
            await state.update_data(subcategory=subcategory_id)
            return await self.get_expense_limit_period(callback.message, state, user_lang, async_session)
        # Back to list of categories
        elif callback.data == 'back':
            return await self.get_expense_limit_category(callback.message, state, user_lang, async_session)
        else:
            return await self.get_expense_limit_subcategory(callback.message, state, user_lang, async_session)

    @staticmethod
    async def get_expense_limit_period(message: Message, state: FSMContext, user_lang, async_session):
        """
        Sets NewExpenseLimitStates.get_period state and asks for new limit period.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession object.

        Returns:
            Message: Reply message.
        """
        await state.set_state(NewExpenseLimitStates.get_period)
        keyboard = await period_keyboard(user_language_code=user_lang, async_session=async_session)
        message_text = NEW_ROUTER_MESSAGES['expense_limit_period'][user_lang]
        return await message.answer(message_text, reply_markup=keyboard)

    async def save_expense_limit_period(self, callback: CallbackQuery, state: FSMContext, user_lang, async_session):
        """
        Saves user period choice and redirects to get_expense_limit_current_period_start.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession object.

        Returns:
            Message: Reply message.
        """
        await callback.message.edit_reply_markup(reply_markup=None)
        if callback.data.startswith('period'):
            period_id = int(callback.data.split(':')[-1])
            await state.update_data(period=period_id)
            return await self.get_expense_limit_current_period_start(callback.message, state, user_lang)
        else:
            return await self.get_expense_limit_period(callback.message, state, user_lang, async_session)

    @staticmethod
    async def get_expense_limit_current_period_start(message: Message, state: FSMContext, user_lang):
        """
        Sets NewExpenseLimitStates.get_current_period_start and asks for user input.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        await state.set_state(NewExpenseLimitStates.get_current_period_start)
        current_date_str = dt.date.today().strftime('%d.%m.%Y')
        keyboard = one_button_keyboard(labels=(current_date_str, current_date_str), callback_data=current_date_str, user_language=user_lang)
        message_text = NEW_ROUTER_MESSAGES['expense_limit_period_start'][user_lang]
        return await message.answer(message_text, reply_markup=keyboard)

    async def save_expense_limit_period_start_from_button(self, callback: CallbackQuery, state: FSMContext, user_lang: str):
        """
        Saves user period choice and redirects to get_expense_limit_value.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        await callback.message.edit_reply_markup(reply_markup=None)
        try:
            date_from_callback = dt.datetime.strptime(callback.data, '%d.%m.%Y').date()
            await state.update_data(period_start=date_from_callback)
            return await self.get_expense_limit_value(callback.message, state, user_lang)
        except (ValueError, Exception) as e:
            logger.error(e)
            return await self.get_expense_limit_current_period_start(callback.message, state, user_lang)

    async def save_expense_limit_period_start_from_message(self, message: Message, state: FSMContext, bot: Bot, user_lang: str):
        """
        Saves user period start and redirects to get_expense_limit_value.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            bot (Bot): Bot.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        try:
            await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.message_id - 1,
                                                reply_markup=None)
        except TelegramBadRequest:
            pass

        period_start_date, error_text = check_input.event_date_from_user_message(message.text.strip(), user_lang)
        if period_start_date is not None:
            await state.update_data(period_start=period_start_date)
            return await self.get_expense_limit_value(message, state, user_lang)
        else:
            return await message.answer(error_text)

    @staticmethod
    async def get_expense_limit_value(message: Message, state: FSMContext, user_lang: str):
        """
        Sets NewExpenseLimitStates.get_value state and asks for new limit value.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        await state.set_state(NewExpenseLimitStates.get_limit_value)
        message_text = NEW_ROUTER_MESSAGES['expense_limit_value'][user_lang]
        return await message.answer(message_text)

    async def save_expense_limit_value(self, message: Message, state: FSMContext, user_lang: str):
        """
        Saves user expense limit value and redirects to get_expense_limit_end_date.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        amount, error_text = check_input.money_amount_from_user_message(message.text.strip(), user_lang)
        if amount is not None:
            await state.update_data(limit_amount=amount)
            return await self.get_expense_limit_end_date(message, state, user_lang)
        else:
            return await message.answer(error_text)

    @staticmethod
    async def get_expense_limit_end_date(message: Message, state: FSMContext, user_lang: str):
        """
        Sets NewExpenseLimitStates.get_end_date state and asks for new limit value.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        await state.set_state(NewExpenseLimitStates.get_end_date)
        keyboard = one_button_keyboard(labels=('Пропустить', 'Skip'), callback_data='no_end', user_language=user_lang)
        message_text = NEW_ROUTER_MESSAGES['expense_limit_end_date'][user_lang]
        return await message.answer(message_text, reply_markup=keyboard)

    async def save_expense_limit_end_date(self, message: Message, state: FSMContext, bot: Bot, user_lang: str):
        """
        Saves user entered end date and redirects to get_expense_limit_cumulative_status.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            bot (Bot): Bot.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        try:
            await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.message_id - 1,
                                                reply_markup=None)
        except TelegramBadRequest:
            pass

        end_date, error_text = check_input.event_date_from_user_message(message.text, past=False, user_lang=user_lang)
        if end_date is not None:
            await state.update_data(end_date=end_date)
            return await self.get_expense_limit_cumulative_status(message, state, user_lang)
        else:
            return await message.answer(error_text)

    async def skip_expense_limit_end_date(self, callback: CallbackQuery, state: FSMContext, user_lang: str):
        """
        Save expense limit end date as None and redirects to get_expense_limit_cumulative_status.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        await callback.message.edit_reply_markup(reply_markup=None)
        if callback.data == 'no_end':
            await state.update_data(end_date=None)
            return await self.get_expense_limit_cumulative_status(callback.message, state, user_lang)

    @staticmethod
    async def get_expense_limit_cumulative_status(message: Message, state: FSMContext, user_lang: str):
        """
        Sets NewExpenseLimitStates.get_cumulative_status state and asks for user choice.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        await state.set_state(NewExpenseLimitStates.get_cumulative)
        keyboard = await binary_keyboard(user_lang, first_button_data=('Копить', 'Cumulative', 'true'),
                                         second_button_data=('Сбрасывать', 'Reset', 'false'))
        message_text = NEW_ROUTER_MESSAGES['expense_limit_cumulative'][user_lang]
        return await message.answer(message_text, reply_markup=keyboard)

    async def save_expense_limit_cumulative_status(self, callback: CallbackQuery, state: FSMContext, user_lang: str,
                                                   async_session):
        """
        Saves user cumulative choice and redirects to save_expense_limit_data.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSessionmaker instance.

        Returns:
            Message: Reply message.
        """
        await callback.message.edit_reply_markup(reply_markup=None)
        cumulative_status = callback.data == 'true'
        await state.update_data(cumulative=cumulative_status)
        return await self.save_expense_limit_data(callback.message, state, user_lang, async_session)

    @staticmethod
    async def save_expense_limit_data(message: Message, state: FSMContext, user_lang: str, async_session):
        """
        Saves user expense limit to database.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSessionmaker instance.

        Returns:
            Message: Reply message.
        """
        total_data = await state.get_data()
        try:
            await ExpenseLimit.create(user_id=total_data['user_id'], period_id=total_data['period'],
                                      current_period_start=total_data['current_period_start'],
                                      limit_value=total_data['limit_amount'], user_title=total_data['title'],
                                      subcategory_id=total_data['subcategory'], end_date=total_data['end_date'],
                                      cumulative=total_data['cumulative'],
                                      async_session=async_session)
            message_text = NEW_ROUTER_MESSAGES['expense_limit_saved'][user_lang]
            return await message.answer(message_text)

        except (ValueError, Exception) as e:
            message_text = NEW_ROUTER_MESSAGES['expense_limit_save_error'][user_lang]
            return await message.answer(message_text)

        finally:
            await state.clear()
