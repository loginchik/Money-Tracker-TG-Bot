from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.types import CallbackQuery

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

from bot.fsm_states import DataDeletionStates
from bot.fsm_states import DeleteExpenseLimitStates
from bot.filters import UserExists
from bot.keyboards import binary_keyboard
from bot.keyboards import expense_limits_keyboard
from bot.static.messages import DELETE_ROUTER_MESSAGES
from bot.static.user_languages import USER_LANGUAGE_PREFERENCES

from db import ExpenseLimit, BotUser


class DeleteRouter(Router):
    """
    Router handles events that are connected with data deletion.
    Commands are: delete_my_data and delete_expense_limit

    On initialization of class object dispatcher is required to register message and callback handlers.
    All handlers are located inside the class, registration is performed in ``register_handlers`` func.
    """
    def __init__(self):
        super().__init__()
        self.register_handlers()
        self.name = 'DeleteRouter'

    def register_handlers(self):
        """
        Register this router handlers in dispatcher.
        """
        # User requests to delete their data, but there is nothing associated with the user
        delete_commands = ['delete_my_data', 'delete_expense_limit']
        self.message.register(self.nothing_to_delete, Command(commands=delete_commands),
                              ~UserExists(), StateFilter(None))

        # Registered user requests to delete their data
        # Ask for confirmation
        self.message.register(self.user_data_deletion_confirmation, Command('delete_my_data'),
                              UserExists(), StateFilter(None))
        # Process confirmation
        self.callback_query.register(self.delete_user_data, DataDeletionStates.decision)

        # Registered user requests to delete one of their expense limits
        # Get expense limit to delete
        self.message.register(self.get_expense_limit_to_delete, Command(commands=['delete_expense_limit']),
                              UserExists(), StateFilter(None))
        # Perform deletion
        self.callback_query.register(self.delete_expense_limit, DeleteExpenseLimitStates.get_user_title)

    @staticmethod
    async def nothing_to_delete(message, user_lang):
        """
        Handler is triggered in case user requested data deletion while not being registered.
        As far as the process is impossible, user is notified about the issue.

        Args:
            message (Message): Message.
            user_lang (str): User language.

        Returns:
            Message: Answer message.
        """
        message_text = DELETE_ROUTER_MESSAGES['nothing_to_delete'][user_lang]
        return await message.answer(message_text)

    @staticmethod
    async def user_data_deletion_confirmation(message: Message, state: FSMContext, user_lang: str):
        """
        Delete all user's data - step 1 / 2

        In case there is user data to delete, user is asked to confirm their decision to prevent accidental deletion.

        Args:
            message (Message): Message.
            state (FSMContext): FSMContext instance.
            user_lang (str): User language.

        Returns:
            Message: Answer message with confirmation inline keyboard.
        """
        first_button_data = ('Удалить мои данные', 'Delete my data', 'delete')
        second_button_data = ('Отменить', 'Cancel', 'cancel')
        decision_keyboard = binary_keyboard(user_language_code=user_lang, first_button_data=first_button_data,
                                            second_button_data=second_button_data)
        await state.set_state(DataDeletionStates.decision)
        message_text = DELETE_ROUTER_MESSAGES['confirmation'][user_lang]
        return await message.answer(message_text, reply_markup=decision_keyboard, parse_mode=ParseMode.HTML)

    @staticmethod
    async def delete_user_data(callback, state, user_lang, async_session):
        """
        Delete all user's data - step 2 / 2

        Catches callback from user deletion decision. If user confirms their decision, all data
        in database, including tables and records, is deleted, user preferred languages is dropped
        from local data dictionary. Otherwise, data is kept.

        Args:
            callback (CallbackQuery): Callback query.
            state (FSMContext): FSMContext instance.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession instance.

        Returns:
            Message: Answer message.
        """
        # Remove inline keyboard anyway.
        await callback.message.edit_reply_markup(reply_markup=None)

        # User confirmed the decision.
        if callback.data == 'delete':
            user_id = callback.from_user.id

            # Successful deletion.
            try:
                # Drop user's data queries
                await BotUser.delete(tg_id=user_id, async_session=async_session)
                # Delete user specified language from languages dict
                del USER_LANGUAGE_PREFERENCES[user_id]
                await state.clear()
                message_text = DELETE_ROUTER_MESSAGES['success'][user_lang]
                return await callback.message.edit_text(message_text)

            # Internal error.
            except Exception as e:
                message_text = DELETE_ROUTER_MESSAGES['error'][user_lang]
                await state.clear()
                return await callback.message.edit_text(message_text)

        # User canceled the decision.
        else:
            message_text = DELETE_ROUTER_MESSAGES['cancel'][user_lang]
            await state.clear()
            return await callback.message.edit_text(message_text)

    @staticmethod
    async def get_expense_limit_to_delete(message, user_lang, async_session, state):
        """
        Delete user's expense limit - step 1 / 2

        Args:
            message (Message): Message.
            user_lang (str): User language.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession instance.
            state (FSMContext): FSMContext instance.

        Returns:
            Message: Answer message.
        """
        # Get limits keyboard
        keyboard = await expense_limits_keyboard(user_id=message.from_user.id, user_lang=user_lang,
                                                 async_session=async_session, cancel_button=True)

        # User has no limits to delete and there is nothing to delete
        if keyboard is None:
            message_text = DELETE_ROUTER_MESSAGES['no_limits'][user_lang]
            return await message.answer(message_text)

        # Set state to wait for user selection and send keyboard
        else:
            message_text = DELETE_ROUTER_MESSAGES['limit_title'][user_lang]
            await state.set_state(DeleteExpenseLimitStates.get_user_title)
            await message.answer(message_text, reply_markup=keyboard)

    @staticmethod
    async def delete_expense_limit(callback, user_lang, state, async_session):
        """
        Delete user's expense limit - step 2 / 2

        Processes user choice: if cancel button is pressed, aborts the process. Otherwise, tries to delete
        specified expense limit.

        Args:
            callback (CallbackQuery): Callback query.
            user_lang (str): User language.
            state (FSMContext): FSMContext instance.
            async_session (async_sessionmaker[AsyncSession]): AsyncSession instance.

        Returns:
            Message: Answer message.
        """
        await callback.message.edit_reply_markup(reply_markup=None)

        # If user pushed cancel button, process is aborted.
        if callback.data == 'cancel_limit':
            message_text = DELETE_ROUTER_MESSAGES['cancel'][user_lang]
            await state.clear()
            return await callback.message.edit_text(message_text)

        # Otherwise, bot is trying to delete data from db
        else:
            try:
                await ExpenseLimit.delete_by_user_id_and_title(user_id=callback.from_user.id,
                                                               user_title=callback.data, async_session=async_session)
                message_text = DELETE_ROUTER_MESSAGES['limit_delete_success'][user_lang]
            except Exception as e:
                message_text = DELETE_ROUTER_MESSAGES['limit_delete_fail'][user_lang]
            await state.clear()
            return await callback.message.edit_text(message_text)
