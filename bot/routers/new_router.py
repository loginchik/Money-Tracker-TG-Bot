import asyncio
import re
import datetime as dt
from loguru import logger

from aiogram import Router, Bot, F
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from db import BotUser, Expense, ExpenseLimit, Income
from bot.filters import UserExists
from bot.fsm_states import (
    RegistrationStates, NewIncomeStates, NewExpenseStates, NewExpenseLimitStates, ExportStates, NewChoice
)
from bot.internal import check_input
import bot.keyboards as keyboards
from bot.routers import CommonRouter, MessageTexts as MT


class NewRecordRouter(Router, CommonRouter):
    def __init__(self):
        super().__init__()
        self.name = 'NewRecordRouter'
        self.register_handlers()

    def register_handlers(self):
        self.message.register(self.abort, Command(commands=['abort']))
        self.message.register(self.add_command, Command(commands=['add']), StateFilter(None), UserExists())

        registration = RegistrationRouter()
        new_expense = NewExpenseRouter()
        new_income = NewIncomeRouter()
        new_expense_limit = NewExpenseLimitRouter()
        self.include_routers(registration, new_expense, new_income, new_expense_limit)
        logger.debug(f'Added ({registration.name}, {new_expense.name}, {new_income.name}, {new_expense_limit.name}) to {self.name}')

    @staticmethod
    async def add_command(message, state, user_lang):
        """
        Sends inline keyboard asking what the user wants to create.
        Sets state to NewChoice.get_item.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message with inline keyboard.
        """
        buttons = (
            ('Расход', 'Expense', 'expense'),
            ('Доход', 'Income', 'income'),
            ('Предел расходов', 'Expense limit', 'expense_limit'),
        )
        keyboard = keyboards.multi_button_keyboard(user_lang=user_lang, one_row_count=1, buttons_data=buttons)
        await state.set_state(NewChoice.get_item)

        m_texts = MT(ru_text='Что вы хотите добавить?', en_text='What would you like to add?')
        message_text = m_texts.__getattribute__(user_lang)
        return await message.answer(text=message_text, reply_markup=keyboard)

    @staticmethod
    async def abort(message, state, user_lang):
        """
        If any state is set, aborts the process and clears the state.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        m_texts = {
            'impossible': MT(
                ru_text='Невозможно прервать этот процесс',
                en_text='Impossible to abort the process'
            ),
            'nothing': MT(
                ru_text='Нет процессов для прерывания',
                en_text='There is nothing to abort'
            ),
            'aborted': MT(
                ru_text='Процесс прекращён, временные данные удалены',
                en_text='Process is aborted, temp data is deleted'
            ),
        }

        current_state = await state.get_state()
        if current_state is not None:
            # Export process cannot be aborted
            if current_state in [st for st in ExportStates.__state_names__]:
                message_text = m_texts['impossible'].__getattribute__(user_lang)
                return await message.answer(message_text)
            # Other processes can
            else:
                await state.clear()
                message_text = m_texts['aborted'].__getattribute__(user_lang)
                return await message.answer(message_text)
        # There is no state set
        else:
            message_text = m_texts['nothing'].__getattribute__(user_lang)
            return await message.answer(message_text)


class RegistrationRouter(Router, CommonRouter):
    def __init__(self):
        super().__init__()
        self.name = 'RegistrationRouter'
        self.register_handlers()

        self.register_callback = 'register'
        self.cancel_register_callback = 'cancel_register'

    def register_handlers(self):
        self.message.register(self.start, Command(commands=['add']), ~UserExists(), StateFilter(None))
        self.callback_query.register(self.save_language_preference, RegistrationStates.preferred_language)
        self.callback_query.register(self.finish, RegistrationStates.decision)

    @staticmethod
    async def start(message: Message, state: FSMContext, user_lang: str):
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
        lang_keyboard = keyboards.binary_keyboard(user_language_code=user_lang,
                                                  first_button_data=('Русский', 'Русский', 'ru'),
                                                  second_button_data=('English', 'English', 'en'),
                                                  )
        await state.set_state(RegistrationStates.preferred_language)
        await state.set_data({'command': message.text})
        # Construct message text
        message_text = 'Выберите предпочтительный язык // Choose preferred language'
        return await message.answer(message_text, reply_markup=lang_keyboard)

    async def save_language_preference(self, callback, state, bot):
        """
        Gets user choice for preferred language and saves it into state data. Redirects
        to get_registration_agreement.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            bot (Bot): Bot instance.
        """
        await self.clear_inline_markup(callback, bot)
        await state.update_data(lang=callback.data)
        return await self.get_agreement(callback.message, state, callback.data)

    async def get_agreement(self, message, state, user_lang):
        """
        Sets RegistrationStates.decision state and asks if user wants to register in database.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Message with inline keyboard.
        """
        keyboard = keyboards.binary_keyboard(
            user_language_code=user_lang,
            first_button_data=('Создать аккаунт', 'Register', self.register_callback),
            second_button_data=('Отмена', 'Cancel', self.cancel_register_callback)
        )
        await state.set_state(RegistrationStates.decision)

        m_texts = MT(
            ru_text='Чтобы пользоваться ботом, вам необходимо зарегистрироваться. Все пользовательские данные хранятся '
                    'в изолированных таблицах, другие пользователи не смогут получить доступ к вашим данным точно '
                    'так же, как вы не сможете получить доступ к данным других пользователей. Вы всегда сможете '
                    'удалить связанные с вами данные командой /delete_my_data command.\n\nСоздать аккаунт?',
            en_text='To access bot functionality, you must register. All data is kept in isolated tables, other users '
                    'won\'t have access to your data same as you won\'t have access to their data. You are always able '
                    'to delete all the data associated with you with /delete_my_data command.'
                    '\n\nWould you like to create an account?'
        )
        message_text = m_texts.__getattribute__(user_lang)
        return await message.answer(message_text, reply_markup=keyboard)

    async def finish(self, callback, state, user_lang, bot):
        """
        Gets user decision in terms of registration. If user want to register, adds their data to db
        and continues initial command process. Otherwise, doesn't register the user and notifies
        about user unavailability to continue.

        Args:
            callback (CallbackQuery): Callback query from registration inline keyboard.
            state (FSMContext): Current state.
            user_lang (str): User language.
            bot (Bot): Bot instance.

        Returns:
            Message:
        """
        # Get user decision from callback
        decision = callback.data
        # Remove markup from message to prevent button re-pushing
        await self.clear_inline_markup(callback, bot)

        m_texts = {
            'success': MT(ru_text='Аккаунт успешно создан', en_text='Account created successfully'),
            'fail': MT(ru_text='Что-то пошло не так. Пожалуйста, попробуйте позже',
                       en_text='Something went wrong. Please try again later'),
            'cancel': MT(ru_text='К сожалению, для доступа к боту необходимо зарегистрироваться :(',
                         en_text='Sorry, you have to register to access the bot :('),
            'after': MT(ru_text=f'Аккаунт успешно создан. Теперь вам доступен функционал бота. '
                                'Вы присылали команду {}. Отправьте её ещё раз, теперь она сработает',
                        en_text=f'Account created successfully. Now you can access bot functionality. '
                                'Previously you sent a command {}. Send it again, now it will work')
        }

        # User registration
        if decision == self.register_callback:
            # Gather user data to insert into DB
            state_data = await state.get_data()
            # Create user and notify the user
            await asyncio.sleep(.5)
            try:
                await BotUser.create(tg_id=callback.from_user.id, tg_username=callback.from_user.username,
                                     tg_first_name=callback.from_user.first_name, lang=state_data['lang'])

                notification_text = m_texts['success'].__getattribute__(state_data['lang'])
                await callback.answer(notification_text)
                message_text = m_texts['after'].__getattribute__(state_data['lang'])
                message_text = message_text.format(state_data['command'])
                return await callback.message.edit_text(message_text)
            except (ValueError, Exception) as e:
                logger.error(e)
                message_text = m_texts['fail'].__getattribute__(state_data['lang'])
                return await callback.message.edit_text(message_text)
            finally:
                await state.clear()

        # User doesn't want to register
        elif decision == self.cancel_register_callback:
            message_text = m_texts['cancel'].__getattribute__(user_lang)
            await state.clear()
            return await callback.message.edit_text(message_text)


class NewExpenseRouter(Router, CommonRouter):
    def __init__(self):
        super().__init__()
        self.name = 'NewExpenseRouter'
        self.register_handlers()
        self.total_steps = 6

    def register_handlers(self):
        self.callback_query.register(self.start, F.data == 'expense', UserExists(), StateFilter(NewChoice.get_item))

        self.message.register(self.save_amount, NewExpenseStates.get_money_amount)

        self.callback_query.register(self.save_category, NewExpenseStates.get_category)

        self.callback_query.register(self.save_subcategory, NewExpenseStates.get_subcategory)

        self.callback_query.register(self.save_datetime, NewExpenseStates.get_datetime)
        self.message.register(self.save_datetime, NewExpenseStates.get_datetime)

        self.callback_query.register(self.save_location, NewExpenseStates.get_location)
        self.message.register(self.save_location, NewExpenseStates.get_location)

        self.callback_query.register(self.finish, NewExpenseStates.get_confirmation)

    async def start(self, callback, state, user_lang, bot):
        """
        Sets state to NewExpenseStates.get_money_amount and asks for money amount input.

        Args:
            callback (CallbackQuery): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.
            bot (Bot): Bot instance.

        Returns:
            Message: Reply message.
        """
        await self.clear_inline_markup(callback, bot)

        await state.clear()
        await state.set_state(NewExpenseStates.get_money_amount)
        await state.update_data(user_id=callback.from_user.id)

        m_texts = MT(ru_text=f'1/{self.total_steps}. Пожалуйста, пришлите сумму (формат: 123.45 или 123)',
                     en_text=f'1/{self.total_steps}. Please, send money amount (format: 123.45 or 123)')

        message_text = m_texts.__getattribute__(user_lang)
        return await callback.message.edit_text(text=message_text)

    async def save_amount(self, message, state, user_lang, bot):
        """
        Saves money count if its correct and redirects to get_expense_category.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.
            bot (Bot): Bot instance.

        Returns:
            Message: Reply message.
        """
        raw_money_count = message.text.strip()
        money_amount, error_text = check_input.money_amount_from_user_message(raw_money_count, user_lang)
        if money_amount is not None:
            # Save user data to state data to get it later
            await state.update_data(amount=money_amount)
            # Display user data in last bot message
            try:
                await bot.edit_message_text(text=f'1/{self.total_steps}. {MT.format_float(money_amount)}',
                                            message_id=message.message_id - 1, chat_id=message.chat.id)
            except TelegramBadRequest:
                pass

            # Ask for category
            return await self.get_category(message, state, user_lang)
        else:
            return await message.answer(error_text)

    async def get_category(self, event, state, user_lang):
        """
        Generates categories inline keyboard and sends it to user.

        Args:
            event (Message | CallbackQuery): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
             Message: Message with inline keyboard.
        """
        keyboard = await keyboards.categories_keyboard(user_lang)
        await state.set_state(NewExpenseStates.get_category)
        m_texts = MT(ru_text=f'2/{self.total_steps}. Выберите категорию',
                     en_text=f'2/{self.total_steps}. Choose expense category')
        message_text = m_texts.__getattribute__(user_lang)

        if isinstance(event, Message):
            return await event.answer(message_text, reply_markup=keyboard)
        elif isinstance(event, CallbackQuery):
            return await event.message.edit_text(text=message_text, reply_markup=keyboard)

    async def save_category(self, callback, state, user_lang, bot):
        """
        Saves chosen category and redirects to get_expense_subcategory.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.
            bot (Bot): Bot.

        Returns:
            Message: Reply message.
        """

        if callback.data.startswith('category'):
            user_expense_category = int(callback.data.split(':')[1])
            user_expense_category_name = callback.data.split(':')[-1]
            await self.clear_inline_markup(source=callback, bot=bot)
            await state.update_data(category=user_expense_category)
            await state.update_data(category_name=user_expense_category_name)

            return await self.get_subcategory(callback, state, user_lang)
        else:
            m_texts = MT(ru_text='Пожалуйста, выберите категорию', en_text='Please, choose category')
            message_text = m_texts.__getattribute__(user_lang)
            return await callback.answer(message_text)

    async def get_subcategory(self, event, state, user_lang):
        """
        Generates subcategory keyboard and sends it to user.

        Args:
            event (Message | CallbackQuery): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Message with inline keyboard.
        """
        await state.set_state(NewExpenseStates.get_subcategory)
        state_data = await state.get_data()
        category_id = state_data['category']
        keyboard = await keyboards.subcategories_keyboard(category_id, user_lang)

        m_texts = MT(ru_text=f'3/{self.total_steps}. Выберите подкатегорию',
                     en_text=f'3/{self.total_steps}. Choose expense subcategory')
        message_text = m_texts.__getattribute__(user_lang)

        if isinstance(event, Message):
            return await event.answer(message_text, reply_markup=keyboard)
        elif isinstance(event, CallbackQuery):
            return await event.message.edit_text(text=message_text, reply_markup=keyboard)

    async def save_subcategory(self, callback, state, user_lang, bot):
        """
        Gets callback data from subcategory keyboard. If 'back' button is pushed,
        sets state to NewExpenseStates.get_category and redirects back to get_expense_category.
        Otherwise, tries to save subcategory_id and redirects to get_expense_datetime.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.
            bot (Bot): Bot.

        Returns:
            Message: Reply message.
        """
        await self.clear_inline_markup(source=callback, bot=bot)

        if callback.data == 'back':
            await state.set_state(NewExpenseStates.get_category)
            return await self.get_category(callback, state, user_lang)
        elif callback.data.startswith('subcategory'):
            subcategory_id = int(callback.data.split(':')[1])
            subcategory_name = callback.data.split(':')[-1]
            await state.update_data(subcategory=subcategory_id)
            await state.update_data(subcategory_name=subcategory_name)

            try:
                state_data = await state.get_data()
                category_name = state_data['category_name']
                m_texts = MT(
                    ru_text='\n'.join([f'2/{self.total_steps}. Категория: {category_name}', f'3/{self.total_steps}. Подкатегория: {subcategory_name}']),
                    en_text='\n'.join([f'2/{self.total_steps}. Category: {category_name}', f'3/{self.total_steps}. Subcategory: {subcategory_name}'])
                )
                await callback.message.edit_text(text=m_texts.__getattribute__(user_lang))
            except TelegramBadRequest:
                pass

            return await self.get_datetime(callback, state, user_lang)
        else:
            m_texts = MT(ru_text='Пожалуйста, выберите подкатегорию', en_text='Please, choose subcategory')
            message_text = m_texts.__getattribute__(user_lang)
            return await callback.answer(message_text)

    async def get_datetime(self, event, state, user_lang):
        """
        Sets state to NewExpenseStates.get_datetime_amount and asks for datetime input.

        Args:
            event (Message | CallbackQuery): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Message with 'now' button.
        """
        keyboard = keyboards.one_button_keyboard(user_language=user_lang, labels=('Сейчас', 'Now'), callback_data='now')
        await state.set_state(NewExpenseStates.get_datetime)

        format_ex = MT.format_date(dt.datetime.now())
        m_texts = MT(ru_text=f'4/{self.total_steps}. Пришлите дату и время совершения покупки (формат: {format_ex})',
                     en_text=f'4/{self.total_steps}. Send date and time of expense (format: {format_ex})')
        message_text = m_texts.__getattribute__(user_lang)

        if isinstance(event, Message):
            return await event.answer(message_text, reply_markup=keyboard)
        elif isinstance(event, CallbackQuery):
            return await event.message.answer(text=message_text, reply_markup=keyboard)

    async def save_datetime(self, event, state, user_lang, bot):
        """
        Saves current datetime as expense event datetime value and redirects to get_expense_location.

        Args:
            event (CallbackQuery | Message): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.
            bot (Bot): Bot.

        Returns:
            Message: Reply message.
        """
        await self.clear_inline_markup(source=event, bot=bot)

        if isinstance(event, CallbackQuery):
            if event.data == 'now':
                dt_stamp = dt.datetime.now()
                await state.update_data(event_datetime=dt_stamp)
                await event.message.edit_text(text=f'4/{self.total_steps}. {MT.format_date(dt_stamp)}')
                return await self.get_location(event, state, user_lang)
            else:
                return await self.get_datetime(event, state, user_lang)

        elif isinstance(event, Message):
            event_datetime, error_text = check_input.event_datetime_from_user_message(event.text, user_lang)
            if event_datetime is not None:
                await state.update_data(event_datetime=event_datetime)
                return await self.get_location(event, state, user_lang)
            else:
                return await event.answer(error_text)

    async def get_location(self, event, state, user_lang):
        """
        Sets NewExpenseStates.get_location state and asks for location. Message contains skip button.

        Args:
            event (Message | CallbackQuery): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        keyboard = keyboards.one_button_keyboard(labels=('Пропустить', 'Skip'),
                                                 callback_data='no_location',
                                                 user_language=user_lang)
        await state.set_state(NewExpenseStates.get_location)

        m_texts = MT(ru_text=f'5/{self.total_steps}. Если хотите, пришлите локацию места, где совершалась покупка, либо нажмите кнопку, чтобы пропустить и продолжить',
                     en_text=f'5/{self.total_steps}. If you wish, send location of place where you made a purchase. Or press button to skip')
        message_text = m_texts.__getattribute__(user_lang)

        if isinstance(event, Message):
            return await event.answer(message_text, reply_markup=keyboard)
        elif isinstance(event, CallbackQuery):
            return await event.message.answer(text=message_text, reply_markup=keyboard)

    async def save_location(self, event, state, bot, user_lang):
        """
        If message contains location, saves it. Otherwise, asks again.

        Args:
            event (Message | CallbackQuery): User message.
            state (FSMContext): Current state.
            bot (Bot): Bot instance.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        await self.clear_inline_markup(source=event, bot=bot)

        if isinstance(event, Message):
            if event.location is not None:
                # Convert geometry from telegram data to shapely point
                geometry_point = check_input.tg_location_to_geometry(event.location)
                await state.update_data(location=geometry_point)
                # Display user data in message
                try:
                    await bot.edit_message_text(text=f'5/{self.total_steps}. {geometry_point.x} {geometry_point.y}', message_id=event.message_id - 1, chat_id=event.chat.id)
                except TelegramBadRequest:
                    pass

                return await self.get_confirmation(event, state, user_lang)

            else:
                return await self.get_location(event, state, user_lang)

        elif isinstance(event, CallbackQuery):
            # Sets event location to None and redirects to save_expense_data.
            await state.update_data(location=None)
            # Display no location data in message
            m_texts = MT(ru_text=f'5/{self.total_steps}. Геопозиция не указана',
                         en_text=f'5/{self.total_steps}. No location')
            await event.message.edit_text(text=m_texts.__getattribute__(user_lang))

            return await self.get_confirmation(event.message, state, user_lang)

    async def get_confirmation(self, event, state, user_lang):
        """
        Sends all collected information to user for them to check the input before saving.

        Args:
            event (Message | CallbackQuery): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        await state.set_state(NewExpenseStates.get_confirmation)

        # Create message heading
        message_head = MT(ru_text=f'6/{self.total_steps}. Подтвердите данные',
                          en_text=f'6/{self.total_steps}. Confirm data')

        # Collect the data into message text
        total_data = await state.get_data()
        message_data = [
            ('Категория' if user_lang == 'ru' else 'Category', total_data['category_name']),
            ('Подкатегория' if user_lang == 'ru' else 'Subcategory', total_data['subcategory_name']),
            ('Сумма' if user_lang == 'ru' else 'Amount', MT.format_float(total_data['amount'])),
            ('Дата и время' if user_lang == 'ru' else 'Date and time', MT.format_date(total_data['event_datetime'])),
        ]
        if total_data['location'] is not None:
            message_data.append(
                ('Координаты' if user_lang == 'ru' else 'Location',
                 f"{total_data['location'].x} {total_data['location'].y}")
            )
        # Collect final message text
        message_text = '\n'.join([': '.join(x) for x in message_data])
        message_text = message_head.__getattribute__(user_lang) + '\n\n' + message_text

        keyboard = keyboards.binary_keyboard(user_lang, ('Сохранить', 'Save', 'save'),
                                             ('Отмена', 'Cancel', 'cancel'))

        if isinstance(event, CallbackQuery):
            return await event.message.edit_text(text=message_text, reply_markup=keyboard)
        elif isinstance(event, Message):
            return await event.answer(text=message_text, reply_markup=keyboard)

    @staticmethod
    async def finish(callback, state, user_lang):
        """
        Saves current state data as expense into DB and closes the process.

        Args:
            callback (CallbackQuery): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        message_text_base = '\n'.join(callback.message.text.split('\n\n')[1:])

        m_texts = {
            'success': MT(ru_text='Сохранено', en_text='Saved'),
            'error': MT(
                ru_text='К сожалению, что-то пошло не так. Данные не сохранены. Пожалуйста, попробуйте ещё раз позднее',
                en_text='Unfortunately, something went wrong. Data is not saved. Please try again later'),
            'cancel': MT(
                ru_text='Данные не сохранены по вашему запросу',
                en_text='Data is not saved due to your request'
            )
        }

        if callback.data == 'save':
            total_data = await state.get_data()
            try:
                await Expense.create(user_id=total_data['user_id'], amount=total_data['amount'],
                                     subcategory_id=total_data['subcategory'], event_time=total_data['event_datetime'],
                                     location=total_data['location'])
                message_text = '\n\n'.join([message_text_base, '<b>' + m_texts['success'].__getattribute__(user_lang) + '</b>'])
                return await callback.message.edit_text(message_text, reply_markup=None)

            except (ValueError, Exception) as e:
                logger.error(e)
                message_text = '\n\n'.join([message_text_base, '<b>' + m_texts['error'].__getattribute__(user_lang) + '</b>'])
                return await callback.message.edit_text(message_text, reply_markup=None)

            finally:
                await state.clear()

        else:
            await state.set_data({})
            await state.clear()
            message_text = '\n\n'.join([message_text_base, '<b>' + m_texts['cancel'].__getattribute__(user_lang) + '</b>'])
            return await callback.message.edit_text(message_text, reply_markup=None)


class NewIncomeRouter(Router, CommonRouter):
    def __init__(self):
        super().__init__()
        self.name = 'NewIncomeRouter'
        self.register_handlers()
        self.total_steps = 4

    def register_handlers(self):
        self.callback_query.register(self.start, F.data == 'income', UserExists(), StateFilter(NewChoice.get_item))

        self.message.register(self.save_amount, NewIncomeStates.get_money_amount)
        self.callback_query.register(self.save_active_status, NewIncomeStates.get_active_status)
        self.callback_query.register(self.save_date, NewIncomeStates.get_event_date)
        self.message.register(self.save_date, NewIncomeStates.get_event_date)
        self.callback_query.register(self.finish, NewIncomeStates.get_confirmation)

    async def start(self, callback, state, user_lang, bot):
        """
        Sets state to NewIncomeStates.get_money_amount and asks for money amount.

        Args:
            callback (CallbackQuery): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.
            bot (Bot): Bot instance.

        Returns:
            Message: Reply message.
        """
        await self.clear_inline_markup(callback, bot)

        await state.set_state(NewIncomeStates.get_money_amount)
        await state.update_data({'user_id': callback.from_user.id})

        m_texts = MT(ru_text=f'1/{self.total_steps}. Пожалуйста, пришлите сумму (формат: 123.45 или 123)',
                     en_text=f'1/{self.total_steps}. Please, send money amount (format: 123.45 or 123)')
        return await callback.message.edit_text(text=m_texts.__getattribute__(user_lang))

    async def save_amount(self, message, state, user_lang, bot):
        """
        Checks if money amount from user message can be converted into positive number. If so,
        saves the value to state data and redirects to get_income_active_status. Otherwise,
        asks for correct money amount.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.
            bot (Bot): Bot instance.

        Returns:
            Message: Reply message.
        """
        raw_money_amount = message.text.strip()
        money_amount, error_text = check_input.money_amount_from_user_message(raw_money_amount, user_lang)
        if money_amount is not None:
            await state.update_data({'amount': money_amount})
            # Display user data in last bot message
            try:
                await bot.edit_message_text(text=f'1/{self.total_steps}. {MT.format_float(money_amount)}',
                                            message_id=message.message_id - 1, chat_id=message.chat.id)
            except TelegramBadRequest:
                pass

            return await self.get_active_status(message, state, user_lang)
        else:
            return await message.answer(error_text)

    async def get_active_status(self, message, state, user_lang):
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
        keyboard = keyboards.binary_keyboard(
            user_language_code=user_lang,
            first_button_data=('Активный', 'Active', 'active'),
            second_button_data=('Пассивный', 'Passive', 'passive')
        )

        m_texts = MT(
            ru_text=f'2/{self.total_steps}. Это активный или пассивный доход?\n\nПассивный доход — это доход, для получения которого не требуется значительных усилий',
            en_text=f'2/{self.total_steps}. Is the income active or passive?\n\nPassive income is revenue that takes negligible effort to acquire'
        )
        return await message.answer(m_texts.__getattribute__(user_lang), reply_markup=keyboard)

    async def save_active_status(self, callback, state, user_lang, bot):
        """
        Converts user inline choice into boolean and redirects to get_income_date.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.
            bot (Bot): Bot.

        Returns:
            Message: Reply message.
        """
        await self.clear_inline_markup(callback, bot)
        status = callback.data == 'passive'
        await state.update_data({'passive': status})

        if user_lang == 'ru':
            message_text = f'2/{self.total_steps}. Пассивный' if status else f'2/{self.total_steps}. Активный'
        else:
            message_text = f'2/{self.total_steps}. Passive' if status else f'2/{self.total_steps}. Active'
        await callback.message.edit_text(text=message_text, reply_markup=None)

        return await self.get_date(callback.message, state, user_lang)

    async def get_date(self, message, state, user_lang):
        """
        Asks for income date.
        :param message: Message from user.
        :param state: FSM context.
        :param user_lang: User language.
        :return: Message with 'today' button.
        """
        await state.set_state(NewIncomeStates.get_event_date)
        today_markup = keyboards.one_button_keyboard(labels=('Сегодня', 'Today'), callback_data='today',
                                                     user_language=user_lang)

        date_ex = MT.format_date(dt.date.today())
        m_texts = MT(ru_text=f'3/{self.total_steps}. Пришлите дату получения дохода (формат: {date_ex})',
                     en_text=f'3/{self.total_steps}. Send date of income (format: {date_ex})')
        return await message.answer(m_texts.__getattribute__(user_lang), reply_markup=today_markup)

    async def save_date(self, event, state, user_lang, bot):
        """
        Saves today's date as event date into income data dict and redirects to get_income_date.
        Keyboard is hidden.Tries to extract date string from user message.  If successful,
        redirects to save_income_data_to_db. Otherwise, asks for correct date.

        Args:
            event (CallbackQuery | Message): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.
            bot (Bot): Bot.

        Returns:
            Message: Reply message.
        """
        await self.clear_inline_markup(event, bot)

        if isinstance(event, CallbackQuery):
            if event.data == 'today':
                dt_stamp = dt.date.today()
                await state.update_data({'event_date': dt_stamp})
                await event.message.edit_text(text=f'3/{self.total_steps}. {MT.format_date(dt_stamp)}')
            return await self.get_confirmation(event, state, user_lang)

        elif isinstance(event, Message):
            raw_event_date = event.text.strip()
            event_date, error_text = check_input.event_date_from_user_message(raw_event_date, user_lang)
            if event_date is not None:
                await state.update_data({'event_date': event_date})
                # Save collected data to db
                try:
                    await bot.edit_message_text(text=f'3/{self.total_steps}. {MT.format_date(event_date)}',
                                                message_id=event.message_id - 1, chat_id=event.chat.id)
                except TelegramBadRequest:
                    pass

                return await self.get_confirmation(event, state, user_lang)
            else:
                return await event.answer(error_text)

    async def get_confirmation(self, event, state, user_lang):
        """
        Sends collected information for user to check data and confirm saving.

        Args:
            event (CallbackQuery | Message): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        await state.set_state(NewIncomeStates.get_confirmation)

        # Create message heading
        message_head = MT(ru_text=f'4/{self.total_steps}. Подтвердите данные',
                          en_text=f'4/{self.total_steps}. Confirm data')

        # Collect the data into message text
        total_data = await state.get_data()
        message_data = [
            ('Сумма' if user_lang == 'ru' else 'Amount', MT.format_float(total_data['amount'])),
            ('Пассивный' if user_lang == 'ru' else 'Passive', '+' if total_data['passive'] else '-'),
            ('Дата' if user_lang == 'ru' else 'Date', MT.format_date(total_data['event_date'])),
        ]

        # Collect final message text
        message_text = '\n'.join([': '.join(x) for x in message_data])
        message_text = message_head.__getattribute__(user_lang) + '\n\n' + message_text

        keyboard = keyboards.binary_keyboard(user_lang, ('Сохранить', 'Save', 'save'),
                                             ('Отмена', 'Cancel', 'cancel'))

        if isinstance(event, CallbackQuery):
            return await event.message.edit_text(text=message_text, reply_markup=keyboard)
        elif isinstance(event, Message):
            return await event.answer(text=message_text, reply_markup=keyboard)

    @staticmethod
    async def finish(callback, state, user_lang):
        """
        Saves income data to DB and finished the creation process.

        Args:
            callback (CallbackQuery): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        message_base = '\n\n'.join(callback.message.text.split('\n\n')[1:])
        m_texts = {
            'success': MT(ru_text='Сохранено', en_text='Saved'),
            'error': MT(ru_text='К сожалению, что-то пошло не так. Данные не сохранены. Пожалуйста, попробуйте ещё раз позже',
                        en_text='Unfortunately, something went wrong. Data is not saved. Please try again'),
            'cancel': MT(ru_text='Данные не сохранены по вашему запросу', en_text='Data is not saved due to your request')
        }

        if callback.data == 'save':
            total_data = await state.get_data()
            try:
                await Income.create(user_id=total_data['user_id'], amount=total_data['amount'],
                                    passive=total_data['passive'], event_date=total_data['event_date'])
                message_text = '\n\n'.join([message_base, '<b>' + m_texts['success'].__getattribute__(user_lang) + '</b>'])
                return await callback.message.edit_text(message_text, reply_markup=None)

            except (ValueError, Exception) as e:
                logger.error(e)
                message_text = '\n\n'.join([message_base, '<b>' + m_texts['error'].__getattribute__(user_lang) + '</b>'])
                return await callback.message.edit_text(message_text, reply_markup=None)

            finally:
                await state.clear()

        else:
            await state.set_data({})
            await state.clear()
            message_text = '\n\n'.join([message_base, '<b>' + m_texts['cancel'].__getattribute__(user_lang) + '</b>'])
            return await callback.message.edit_text(message_text, reply_markup=None)


class NewExpenseLimitRouter(Router, CommonRouter):
    def __init__(self):
        super().__init__()
        self.name = 'NewExpenseLimitRouter'
        self.register_handlers()
        self.total_steps = 8

    def register_handlers(self):
        self.callback_query.register(self.start, F.data == 'expense_limit', UserExists(), StateFilter(NewChoice.get_item))

        self.message.register(self.save_title, NewExpenseLimitStates.get_title)

        self.callback_query.register(self.save_category, NewExpenseLimitStates.get_category)

        self.callback_query.register(self.save_subcategory, NewExpenseLimitStates.get_subcategory)

        self.callback_query.register(self.save_period, NewExpenseLimitStates.get_period)

        self.callback_query.register(self.save_start_date, NewExpenseLimitStates.get_current_period_start)
        self.message.register(self.save_start_date, NewExpenseLimitStates.get_current_period_start)

        self.message.register(self.save_limit_value, NewExpenseLimitStates.get_limit_value)

        self.message.register(self.save_end_date, NewExpenseLimitStates.get_end_date)
        self.callback_query.register(self.save_end_date, NewExpenseLimitStates.get_end_date)

        self.callback_query.register(self.save_cumulative_status, NewExpenseLimitStates.get_cumulative)
        self.callback_query.register(self.finish, NewExpenseLimitStates.get_confirmation)

    async def start(self, callback, state, user_lang, bot):
        """
        Sets NewExpenseLimitStates.get_title and asks for new limit title.

        Args:
            callback (CallbackQuery): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.
            bot (Bot): Bot.

        Returns:
            Message: Reply message.
        """
        await self.clear_inline_markup(callback, bot)

        await state.set_state(NewExpenseLimitStates.get_title)
        await state.update_data(user_id=callback.from_user.id)

        # Get basic text
        m_texts = MT(ru_text=f'1/{self.total_steps}. Пожалуйста, пришлите название нового предела расходов. Оно должно быть уникальным и не длиннее 100 символов.',
                     en_text=f'1/{self.total_steps}. Please, send expense limit title. It should be unique and no more than 100 characters length.')
        message_text = m_texts.get(user_lang)

        # Add existing titles
        exist_titles = await ExpenseLimit.select_titles(user_id=callback.from_user.id)
        if len(exist_titles) > 0:
            exist_titles_string = ', '.join(['<i>' + t + '</i>' for t in exist_titles])
            m_texts = MT(ru_text='\n\nУ вас уже есть пределы с названиями {}',
                         en_text='\n\nYou already have limits named {}')
            message_text += m_texts.get(user_lang).format(exist_titles_string)

        return await callback.message.edit_text(text=message_text, parse_mode=ParseMode.HTML)

    async def save_title(self, message, state, bot, user_lang):
        """
        Saves expense limit title if it satisfies conditions and redirects to get_expense_limit_category.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            bot (Bot): Bot.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        user_title = message.text.strip().replace('\n', ' ')
        user_title = re.sub(r'\s+', ' ', user_title)
        # Check title matches length criteria
        if len(user_title) in range(1, 101):

            # Check title matches unique criteria
            exist_titles = await ExpenseLimit.select_titles(user_id=message.from_user.id)
            if user_title in exist_titles:
                m_texts = MT(ru_text=f'У вас уже есть предел с названием <i>{user_title}</i>',
                             en_text=f'You already have limits named <i>{user_title}</i>')
                return message.answer(m_texts.get(user_lang), reply_markup=None)

            # Save title
            await state.update_data(title=message.text.strip())
            # Display user title in message
            try:
                await bot.edit_message_text(text=f'1/{self.total_steps}. {user_title}', message_id=message.message_id - 1, chat_id=message.chat.id, reply_markup=None)
            except TelegramBadRequest:
                pass
            return await self.get_category(message, state, user_lang)

        else:
            m_texts = MT(ru_text='Это название слишком длинное. Пожалуйста, пришлите корректное',
                         en_text='This title is too long. Please, send correct one')
            message_text = m_texts.get(user_lang)
            return await message.reply(message_text)

    async def get_category(self, event, state, user_lang):
        """
        Sets NewExpenseLimitStates.get_category state and asks for new limit category.

        Args:
            event (Message | CallbackQuery): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        await state.set_state(NewExpenseLimitStates.get_category)

        info_texts = MT(ru_text='Предел расходов связывается с подкатегориями расходов (не больше 5)',
                        en_text='Expense limit is linked with expense subcategories (max 5)')
        m_texts = MT(ru_text=f'2/{self.total_steps}. Выберите категорию',
                     en_text=f'2/{self.total_steps}. Choose category')
        total_text = info_texts.get(user_lang) + '\n\n' + m_texts.get(user_lang)

        keyboard = await keyboards.categories_keyboard(user_language_code=user_lang)

        if isinstance(event, Message):
            return await event.answer(total_text, reply_markup=keyboard)
        elif isinstance(event, CallbackQuery):
            return await event.message.edit_text(total_text, reply_markup=keyboard)

    async def save_category(self, callback, state, user_lang, bot):
        """
        Saves user category choice and redirects to get_expense_limit_subcategory.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.
            bot (Bot): Bot object.

        Returns:
            Message: Reply message.
        """
        # Remove markup anyway
        await self.clear_inline_markup(callback, bot)
        if callback.data.startswith('category'):
            category_id = int(callback.data.split(':')[1])
            await state.update_data(category=category_id)
            await state.update_data(category_name=callback.data.split(':')[-1])
            return await self.get_subcategory(callback, state, user_lang)
        else:
            return await self.get_category(callback.message, state, user_lang)

    async def get_subcategory(self, callback, state, user_lang):
        """
        Sets NewExpenseLimitStates.get_subcategory state and asks for subcategory.

        Args:
            callback (CallbackQuery | Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        state_data = await state.get_data()
        category_id = state_data['category']
        keyboard = await keyboards.subcategories_keyboard(category_id, user_lang, end_button=True)

        await state.set_state(NewExpenseLimitStates.get_subcategory)

        m_texts = MT(ru_text=f'2/{self.total_steps}. Выберите подкатегорию. Повторный выбор уберёт её из списка',
                     en_text=f'2/{self.total_steps}. Choose subcategory. Tap again to remove it from the list')
        current_list = await self.__selected_subcategories(state)

        message_text = m_texts.get(user_lang) + '\n\n' + current_list
        if isinstance(callback, CallbackQuery):
            return await callback.message.edit_text(message_text, reply_markup=keyboard)
        elif isinstance(callback, Message):
            return await callback.answer(message_text, reply_markup=keyboard)

    async def save_subcategory(self, callback, state, user_lang, bot):
        """
        Saves user subcategory choice and redirects to get_expense_limit_period.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.
            bot (Bot): Bot object.

        Returns:
            Message: Reply message.
        """
        # Remove markup anyway
        await self.clear_inline_markup(callback, bot)

        if callback.data.startswith('subcategory'):
            subcategory_id = int(callback.data.split(':')[1])
            subcategory_name = callback.data.split(':')[-1]
            total_data = await state.get_data()
            category_name = total_data['category_name']

            current_subcats = total_data.get('subcategories', [])
            current_record = f'{category_name}:{subcategory_name}:{subcategory_id}'
            if current_record in current_subcats:
                current_subcats.remove(current_record)
            else:
                if len(current_subcats) < 5:
                    current_subcats.append(current_record)
            await state.update_data({'subcategories': current_subcats})

            return await self.get_subcategory(callback, state, user_lang)

        # Back to list of categories
        elif callback.data == 'back':
            return await self.get_category(callback, state, user_lang)

        # Save
        elif callback.data == 'end':
            # Check that at least one subcategory is checked
            total_data = await state.get_data()
            if len(total_data.get('subcategories', [])) == 0:
                await callback.message.edit_text('Выберите хотя бы одну подкатегорию' if user_lang == 'ru'
                                                 else 'Choose 1 subcategory at least')
                return await self.get_subcategory(callback.message, state, user_lang)

            # Display selection in the message
            m_texts = MT(ru_text=f'2/{self.total_steps}. Выбранные подкатегории',
                         en_text=f'2/{self.total_steps}. Chosen subcategories')
            current_choice = await self.__selected_subcategories(state)
            message_text = m_texts.get(user_lang) + '\n\n' + current_choice
            await callback.message.edit_text(text=message_text, reply_markup=None)

            return await self.get_period(callback.message, state, user_lang)

        else:
            return await self.get_subcategory(callback, state, user_lang)

    async def get_period(self, event, state, user_lang):
        """
        Sets NewExpenseLimitStates.get_period state and asks for new limit period.

        Args:
            event (Message | CallbackQuery): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        await state.set_state(NewExpenseLimitStates.get_period)
        keyboard = await keyboards.period_keyboard(user_language_code=user_lang)

        m_texts = MT(ru_text=f'3/{self.total_steps}. Предел расходов сбрасывается раз в определённый период времени. '
                             f'Как долго должен длиться один период?',
                     en_text=f'3/{self.total_steps}. Expense limit is reset after some period of time. '
                             f'How long should one limit last?')

        if isinstance(event, Message):
            return await event.answer(m_texts.get(user_lang), reply_markup=keyboard)
        elif isinstance(event, CallbackQuery):
            return await event.message.edit_text(m_texts.get(user_lang), reply_markup=keyboard)

    async def save_period(self, callback, state, user_lang, bot):
        """
        Saves user period choice and redirects to get_expense_limit_current_period_start.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.
            bot (Bot): Bot object.

        Returns:
            Message: Reply message.
        """
        await self.clear_inline_markup(callback, bot)
        if callback.data.startswith('period'):
            period_id = int(callback.data.split(':')[1])
            await state.update_data(period=period_id)
            await state.update_data(period_name=callback.data.split(':')[-1])
            return await self.get_start_date(callback, state, user_lang)
        else:
            return await self.get_period(callback, state, user_lang)

    async def get_start_date(self, callback, state, user_lang):
        """
        Sets NewExpenseLimitStates.get_current_period_start and asks for user input.

        Args:
            callback (CallbackQuery): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        await state.set_state(NewExpenseLimitStates.get_current_period_start)
        current_date_str = dt.date.today().strftime('%d.%m.%Y')
        keyboard = keyboards.one_button_keyboard(labels=(current_date_str, current_date_str),
                                                 callback_data=current_date_str, user_language=user_lang)
        date_ex = MT.format_date(dt.date.today())
        m_texts = MT(ru_text=f'4/{self.total_steps}. Когда начать применять предел? Вы можете выбрать с помощью кнопок '
                             f'или прислать дату вручную (формат: {date_ex}).',
                     en_text=f'4/{self.total_steps}. When to start applying expense limit? You can choose by buttons '
                             f'or send a date manually (format: {date_ex}).')

        return await callback.message.edit_text(m_texts.get(user_lang), reply_markup=keyboard)

    async def save_start_date(self, event, state, user_lang, bot):
        """
        Saves user period choice and redirects to get_expense_limit_value.

        Args:
            event (CallbackQuery | Message): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.
            bot (Bot): Bot object.

        Returns:
            Message: Reply message.
        """
        await self.clear_inline_markup(event, bot)

        if isinstance(event, CallbackQuery):
            try:
                date_from_callback = dt.datetime.strptime(event.data, '%d.%m.%Y').date()
                await state.update_data(period_start=date_from_callback)
                await event.message.edit_text(text=f'4/{self.total_steps}. {MT.format_date(date_from_callback)}')
                return await self.get_limit_value(event.message, state, user_lang)
            except (ValueError, Exception) as e:
                logger.error(e)
                return await self.get_start_date(event, state, user_lang)

        elif isinstance(event, Message):
            period_start_date, error_text = check_input.event_date_from_user_message(event.text.strip(), user_lang)
            if period_start_date is not None:
                total_data = await state.get_data()
                period_days = int(total_data.get('period_name', 0))
                if period_start_date + dt.timedelta(days=period_days) <= dt.date.today():
                    period_start_formatted = MT.format_date(period_start_date)
                    m_texts = MT(ru_text=f'Если начинать отчёт предела с периодичностью {period_days} '
                                         f'с {period_start_formatted}, то он уже закончился. Введите более позднюю дату',
                                 en_text=f'If limit with period = {period_days} starts on {period_start_formatted}, '
                                         f'it would have already ended. Please, enter the later date.')
                    return await event.reply(text=m_texts.get(user_lang))

                await state.update_data(period_start=period_start_date)
                try:
                    await bot.edit_message_text(text=f'4/{self.total_steps}. {MT.format_date(period_start_date)}',
                                                message_id=event.message_id - 1, chat_id=event.chat.id)
                except TelegramBadRequest:
                    pass

                return await self.get_limit_value(event, state, user_lang)
            else:
                return await event.answer(error_text)

    async def get_limit_value(self, message, state, user_lang):
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

        m_texts = MT(ru_text=f'5/{self.total_steps}. Какую максимальную сумму вы бы хотели тратить на подкатегорию '
                             f'в один период? (формат: 123.45 или 123)',
                     en_text=f'5/{self.total_steps}. What is the maximum amount of money you would like to spend '
                             f'for the subcategory in one period? (format: 123.45 or 123)')
        return await message.answer(m_texts.get(user_lang))

    async def save_limit_value(self, message, state, user_lang, bot):
        """
        Saves user expense limit value and redirects to get_expense_limit_end_date.

        Args:
            message (Message): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.
            bot (Bot): Bot object.

        Returns:
            Message: Reply message.
        """
        amount, error_text = check_input.money_amount_from_user_message(message.text.strip(), user_lang)
        if amount is not None:
            await state.update_data(limit_amount=amount)
            try:
                await bot.edit_message_text(text=f'5/{self.total_steps}. {MT.format_float(amount)}',
                                            chat_id=message.chat.id, message_id=message.message_id - 1)
            except TelegramBadRequest:
                pass

            return await self.get_end_date(message, state, user_lang)
        else:
            return await message.answer(error_text)

    async def get_end_date(self, message, state, user_lang):
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
        keyboard = keyboards.one_button_keyboard(labels=('Пропустить', 'Skip'), callback_data='no_end',
                                                 user_language=user_lang)

        m_texts = MT(ru_text=f'6/{self.total_steps}. Если хотите, установите дату окончания действия предела расходов. '
                             f'После этой даты предел расходов будет автоматически удалён (формат: 01.12.2023). '
                             f'Нажмите кнопку, чтобы пропустить',
                     en_text=f'6/{self.total_steps}. If you wish, set the end date of expense limit. After this date '
                             f'expense limit will be deleted automatically (format: 01.12.2023). Press button to skip')
        return await message.answer(m_texts.get(user_lang), reply_markup=keyboard)

    async def save_end_date(self, event, state, bot, user_lang):
        """
        Saves user entered end date and redirects to get_expense_limit_cumulative_status.

        Args:
            event (Message | CallbackQuery): User message.
            state (FSMContext): Current state.
            bot (Bot): Bot.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        await self.clear_inline_markup(event, bot)

        if isinstance(event, Message):
            end_date, error_text = check_input.event_date_from_user_message(event.text, past=False, user_lang=user_lang)
            if end_date is not None:
                await state.update_data(end_date=end_date)
                try:
                    await bot.edit_message_text(text=f'6/{self.total_steps}. {MT.format_float(end_date)}',
                                                chat_id=event.chat.id, message_id=event.message_id - 1)
                except TelegramBadRequest:
                    pass

                return await self.get_cumulative_status(event, state, user_lang)
            else:
                return await event.answer(error_text)

        elif isinstance(event, CallbackQuery):
            if event.data == 'no_end':
                await state.update_data(end_date=None)
                await event.message.edit_text(text=f'6/{self.total_steps}. -')
                return await self.get_cumulative_status(event.message, state, user_lang)
            else:
                return await self.get_end_date(event.message, state, user_lang)

    async def get_cumulative_status(self, message, state, user_lang):
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
        keyboard = keyboards.binary_keyboard(user_lang, first_button_data=('Копить', 'Cumulative', 'true'),
                                             second_button_data=('Сбрасывать', 'Reset', 'false'))

        m_texts = MT(ru_text=f'7/{self.total_steps}. Вы хотите сбрасывать доступный баланс предела, когда период '
                             f'заканчивается, или копить баланс? Если предел накопительный, то когда у вас останется, '
                             f'например, 10 от текущего периода в следующем периоде баланс будет 10 + максимальная '
                             f'сумма, которую вы установили на шаге 5',
                     en_text=f'7/{self.total_steps}. Do you want to reset available balance to limit value when period '
                             f'ends or to accumulate it? Cumulative means that if you have for example 10 left from '
                             f'the period, new period\'s balance will be 10 + max amount you set on step 5'
                     )

        return await message.answer(m_texts.get(user_lang), reply_markup=keyboard)

    async def save_cumulative_status(self, callback, state, user_lang, bot):
        """
        Saves user cumulative choice and redirects to save_expense_limit_data.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.
            bot (Bot): Bot.

        Returns:
            Message: Reply message.
        """
        await self.clear_inline_markup(callback, bot)
        cumulative_status = callback.data == 'true'
        await state.update_data(cumulative=cumulative_status)
        await callback.message.edit_text(f'7/{self.total_steps}. {"+" if cumulative_status else "-"}')
        return await self.get_confirmation(callback, state, user_lang)

    async def get_confirmation(self, callback, state, user_lang):
        """
        Asks for confirmation before saving.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        await state.set_state(NewExpenseLimitStates.get_confirmation)

        # Create message heading
        message_head = MT(ru_text=f'8/{self.total_steps}. Подтвердите данные',
                          en_text=f'8/{self.total_steps}. Confirm data')

        # Collect the data into message text
        total_data = await state.get_data()
        message_data = [
            ('Название' if user_lang == 'ru' else 'Title', total_data['title']),
            ('Сумма предела' if user_lang == 'ru' else 'Limit amount', MT.format_float(total_data['limit_amount'])),
            ('Дата начала периода' if user_lang == 'ru' else 'Date and time', MT.format_date(total_data['period_start'])),
            ('Длительность (дней)' if user_lang == 'ru' else 'Period length (days)', str(total_data['period_name'])),
            ('Подкатегории' if user_lang == 'ru' else 'Subcategories', ', '.join([s.split(':')[1] for s in total_data['subcategories']])),
            ('Кумулятивный' if user_lang == 'ru' else 'Cumulative', "+" if total_data['cumulative'] else "-"),
        ]

        if total_data['end_date'] is not None:
            message_data.append(
                ('Дата окончания действия' if user_lang == 'ru' else 'Expiration date',
                 MT.format_date(total_data['end_date']))
            )

        # Collect final message text
        message_text = '\n'.join([': '.join(x) for x in message_data])
        message_text = message_head.__getattribute__(user_lang) + '\n\n' + message_text

        keyboard = keyboards.binary_keyboard(user_lang, ('Сохранить', 'Save', 'save'),
                                             ('Отмена', 'Cancel', 'cancel'))

        return await callback.message.edit_text(text=message_text, reply_markup=keyboard)

    @staticmethod
    async def finish(callback, state, user_lang):
        """
        Saves user expense limit to database.

        Args:
            callback (CallbackQuery): User message.
            state (FSMContext): Current state.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        message_base = '\n\n'.join(callback.message.text.split('\n\n')[1:])

        m_texts = {
            'success': MT('Сохранено', 'Saved'),
            'error': MT(ru_text='К сожалению, что-то пошло не так. Предел расходов не создан. '
                                'Пожалуйста, попробуйте ещё раз позже',
                        en_text='Unfortunately, something went wrong. Expense limit is not created. '
                                'Please, try again later'),
            'cancel': MT('Данные не сохранены по вашему запросу', 'Data is not saved due to your request')
        }

        if callback.data == 'save':
            total_data = await state.get_data()
            subcategories = [int(s.split(':')[-1]) for s in total_data.get('subcategories', [])]
            try:
                await ExpenseLimit.create(user_id=total_data['user_id'], period_id=total_data['period'],
                                          current_period_start=total_data['period_start'],
                                          limit_value=total_data['limit_amount'], user_title=total_data['title'],
                                          subcategories=subcategories, end_date=total_data['end_date'],
                                          cumulative=total_data['cumulative'])
                message_text = '\n\n'.join([message_base, '<b>' + m_texts['success'].get(user_lang) + '</b>'])
                return await callback.message.edit_text(message_text, reply_markup=None)

            except (ValueError, Exception) as e:
                logger.error(e)
                message_text = '\n\n'.join([message_base, '<b>' + m_texts['error'].get(user_lang) + '</b>'])
                return await callback.message.edit_text(message_text, reply_markup=None)

            finally:
                await state.clear()
        else:
            await state.set_data({})
            await state.clear()
            message_text = '\n\n'.join([message_base, '<b>' + m_texts['cancel'].get(user_lang) + '</b>'])
            return await callback.message.edit_text(message_text, reply_markup=None)

    @staticmethod
    async def __selected_subcategories(state):
        """
        Generates string containing selected subcategories.

        Args:
            state (FSMContext): Current state.

        Returns:
            str: Enumerated subcategories list.
        """
        total_data = await state.get_data()
        subcategories = total_data.get('subcategories', [])

        list_items = []
        for subcat in subcategories:
            category_name, subcategory_name, _ = subcat.split(':')
            list_items.append('/'.join([category_name, subcategory_name]))

        user_selected = [f'{i + 1}. {info}' for i, info in enumerate(list_items)]
        empty_slots = [f'{i + 1}. -' for i in range(len(user_selected), 5)]

        return '\n'.join(user_selected + empty_slots)
