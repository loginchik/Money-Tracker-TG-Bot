import os
import datetime as dt

from loguru import logger
from aiogram import Router
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.types import FSInputFile
from aiogram.types import InputMediaDocument
from aiogram.filters import Command, StateFilter

from bot.filters import UserExists
from bot.fsm_states import ExportStates
from bot.routers import MessageTexts as MT
from db import Expense, Income
from configs import BASE_DIR


class NoDataException(Exception):
    pass


class ExportRouter(Router):
    def __init__(self):
        super().__init__()
        self.name = 'ExportRouter'
        self.register_handlers()

    def register_handlers(self):
        # Not registered user requests to export their data, but there is no data to export
        self.message.register(self.nothing_to_export, Command('export_my_data'), ~UserExists(), StateFilter(None))

        # Registered user requests to export their data
        self.message.register(self.export_users_data, Command('export_my_data'), UserExists(), StateFilter(None))
        # User asks for something, while expense data is exported
        self.message.register(self.exporting_expenses_message, ExportStates.export_expenses)
        self.callback_query.register(self.exporting_expenses_message, ExportStates.export_expenses)
        # User asks for something, while incomes data is exported
        self.message.register(self.exporting_incomes_message, ExportStates.export_incomes)
        self.callback_query.register(self.exporting_incomes_message, ExportStates.export_incomes)

    @staticmethod
    async def nothing_to_export(message, user_lang):
        """
        Notifies user there is no data to export because they are not registered.

        Args:
            message (Message): Message to send notification.
            user_lang (lang): Language of the user to notify.

        Returns:
            Message: Notification message.
        """
        m_texts = MT(
            ru_text='Вы не зарегистрированы. Нет данных, связанных с вами',
            en_text='You are not registered. There is no data associated with you'
        )
        await message.answer(m_texts.get(user_lang))

    async def export_users_data(self, message, user_lang, state, bot):
        """
        Runs user's data exporting process.

        Args:
            message (Message): User's message.
            user_lang (str): User's language.
            state (FSMContext): Current state.
            bot (Bot): Bot instance.

        Returns:
            Message: Reply message.
        """
        # Send notification about process taking a while
        user_id = message.from_user.id
        wait_m_texts = MT(
            ru_text='Это займёт некоторое время, пожалуйста, подождите',
            en_text='This may take a while, please wait'
        )
        await message.answer(wait_m_texts.get(user_lang))

        # Set state to prevent process aborting
        await state.set_state(ExportStates.export_expenses)

        # Export expenses
        try:
            expense_success = await self.export_expenses(message, user_id, user_lang, bot, state)
        except Exception as e:
            logger.error(e)
            expense_success = False

        # Export incomes
        try:
            income_success = await self.export_incomes(message, user_id, user_lang, bot, state)
        except Exception as e:
            logger.error(e)
            income_success = False

        if not any([income_success, expense_success]):
            m_texts = MT(
                ru_text='К сожалению, что-то пошло не так. Попробуйте ещё раз позже',
                en_text='Unfortunately, something went wrong. Please try again later'
            )
            await message.answer(m_texts.get(user_lang))

    @staticmethod
    async def exporting_expenses_message(message, user_lang):
        """
        Notifies user that expense export is in progress.

        Args:
            message (Message): Message to send notification.
            user_lang (lang): Language of the user to notify.

        Returns:
            Message: Notification message.
        """
        m_texts = MT(
            ru_text='Собираю ваши расходы... Пожалуйста, подождите',
            en_text='Gathering your expenses... Please wait...'
        )
        await message.answer(m_texts.get(user_lang))

    @staticmethod
    async def exporting_incomes_message(message, user_lang):
        """
        Notifies user that income export is in progress.

        Args:
            message (Message): Message to send notification.
            user_lang (lang): Language of the user to notify.

        Returns:
            Message: Notification message.
        """
        m_texts = MT(
            ru_text='Собираю ваши доходы... Пожалуйста, подождите',
            en_text='Gathering your incomes... Please wait...'
        )
        await message.answer(m_texts.get(user_lang))

    async def export_expenses(self, message, user_id, user_lang, bot, state):
        """
        Exports user's expenses into files and sends them.

        Args:
            message (Message): User message.
            user_id (int): User's id.
            user_lang (str): User's language.
            bot (Bot): Bot instance.
            state (FSMContext): Current state.

        Returns:
            Message: Notification message.
        """
        temp_files_csv = []
        temp_files_json = []
        columns = self.expense_data_columns(user_lang=user_lang)
        try:
            # Get expenses data generator
            expenses_data = Expense.select_for_export(user_id=user_id, user_lang=user_lang)

            # Save each chunk as separate file
            chunk_id = 1
            for expense_chunk in expenses_data:
                if expense_chunk.shape[0] == 0:
                    raise NoDataException('No expenses data')

                # Rename columns
                expense_chunk = expense_chunk.rename(columns=columns)
                expense_chunk['i'] = range(1, expense_chunk.shape[0] + 1)

                # Get temp files filenames
                exp_temp_filename_gpkg, exp_temp_filename_csv = self.expense_temp_filenames(user_id, chunk_id=chunk_id)

                # Save temp files
                expense_chunk.to_file(exp_temp_filename_gpkg, encoding='utf-8', driver='GeoJSON')
                expense_chunk.drop(columns=['location']).to_csv(exp_temp_filename_csv, index=False)
                # Add their paths to lists
                temp_files_json.append(exp_temp_filename_gpkg)
                temp_files_csv.append(exp_temp_filename_csv)
                chunk_id += 1

            # Collect medias
            input_medias = []
            for i, csv_file, gpkg_file in zip(range(1, chunk_id + 1), temp_files_csv, temp_files_json):
                exp_filename_gpkg, exp_filename_csv = self.expense_out_filenames(chunk_id=i)
                fs_csv = FSInputFile(path=csv_file, filename=exp_filename_csv)
                fs_gpkg = FSInputFile(path=gpkg_file, filename=exp_filename_gpkg)
                input_medias.append(InputMediaDocument(media=fs_csv))
                input_medias.append(InputMediaDocument(media=fs_gpkg))

            # Send medias
            await self.__send_media_groups(media=input_medias, bot=bot, chat_id=message.chat.id)
            m_texts = MT('Ваши расходы', 'Your expenses')
            await message.answer(text=m_texts.get(user_lang))
            return True

        # User has no data to export
        except NoDataException:
            error_message = MT(ru_text='Вы ещё не записали ни одного расхода',
                               en_text='You have not logged any expense yet')
            await message.answer(error_message.get(user_lang))
            return True

        # Something went wrong
        except Exception as e:
            logger.error(e)
            m_texts = MT(ru_text='Не удалось экспортировать расходы...', en_text='Error exporting expenses...')
            await message.answer(m_texts.get(user_lang))
            return False

        finally:
            # Remove temp files
            self.__delete_temp_files(temp_files_json + temp_files_csv)
            # Set state on exporting incomes
            await state.set_state(ExportStates.export_incomes)

    async def export_incomes(self, message, user_id, user_lang, bot, state):
        temp_files = []
        columns = self.income_data_columns(user_lang=user_lang)

        try:
            # Query data
            incomes_data = Income.select_by_user_id(user_id=user_id)

            # Save each chunk into separate file
            chunk_id = 1
            for income_chunk in incomes_data:
                if income_chunk.shape[0] == 0:
                    raise NoDataException('No incomes data')

                # Update data for user
                passive_map = {True: 'Пассивный', False: 'Активный'} \
                    if user_lang == 'ru' else {True: 'Passive', False: 'Active'}
                income_chunk['passive_status'] = income_chunk['passive_status'].map(passive_map)
                income_chunk = income_chunk.rename(columns=columns)
                income_chunk['i'] = range(1, income_chunk.shape[0] + 1)

                income_temp_filename = f'{user_id}_{dt.datetime.now().strftime("%d%H%M%S")}_expenses_{chunk_id}.csv'
                income_chunk.to_csv(income_temp_filename)
                temp_files.append(income_temp_filename)
                chunk_id += 1

            # Collect media
            input_medias = []
            for i, csv_file in zip(range(chunk_id), temp_files):
                income_out_filename = f'{dt.datetime.now().strftime("%d_%m_%Y_%H_%M_%S")}_incomes_{i}.csv'
                fs = FSInputFile(path=csv_file, filename=income_out_filename)
                input_medias.append(InputMediaDocument(media=fs))

            # Send media
            await self.__send_media_groups(media=input_medias, bot=bot, chat_id=message.chat.id)
            m_texts = MT('Ваши доходы', 'Your incomes')
            await message.answer(text=m_texts.get(user_lang))
            return True

        except NoDataException:
            error_message = MT(ru_text='Вы ещё не записали ни одного дохода', en_text='You have not logged any income yet')
            await message.answer(error_message.get(user_lang))
            return True

        except Exception as e:
            logger.error(e)
            m_texts = MT('Не удалось экспортировать доходы...', 'Error exporting incomes...')
            await message.answer(m_texts.get(user_lang))
            return False

        finally:
            # Remove temp file
            self.__delete_temp_files(temp_files)
            # Clear the state
            await state.clear()

    @staticmethod
    def expense_temp_filenames(user_id: int, chunk_id) -> tuple[str, str]:
        exp_temp_filename = f'{user_id}_{dt.datetime.now().strftime("%d%H%M%S")}_expenses_{chunk_id}'
        exp_temp_filename_gpkg = os.path.join(BASE_DIR, 'temp', exp_temp_filename + '.geojson')
        exp_temp_filename_csv = os.path.join(BASE_DIR, 'temp', exp_temp_filename + '.csv')
        return exp_temp_filename_gpkg, exp_temp_filename_csv

    @staticmethod
    def expense_out_filenames(chunk_id) -> tuple[str, str]:
        out_filename = f'{dt.datetime.now().strftime("%d_%m_%Y_%H_%M_%S")}_expenses_{chunk_id}'
        exp_filename_csv = out_filename + '.csv'
        exp_filename_gpkg = out_filename + '.geojson'
        return exp_filename_gpkg, exp_filename_csv

    @staticmethod
    def expense_data_columns(user_lang):
        return {
            'event_time': 'Дата платежа',
            'amount': 'Сумма',
            'title_ru': 'Подкатегория расходов',
            'title_ru_1': 'Категория расходов'
        } if user_lang == 'ru' else {
            'event_time': 'Payment date',
            'amount': 'Money amount',
            'title_ru': 'Expense subcategory',
            'title_ru_1': 'Expense category'
        }

    @staticmethod
    def income_data_columns(user_lang):
        return {
            'event_date': 'Дата получения дохода',
            'amount': 'Сумма',
            'passive_status': 'Тип дохода'
        } if user_lang == 'ru' else {
            'event_date': 'Income date',
            'amount': 'Money amount',
            'passive_status': 'Income type'
        }

    @staticmethod
    def __delete_temp_files(files_list):
        for file in files_list:
            if os.path.exists(file) and os.path.isfile(file):
                os.remove(file)
                logger.info(f'Deleted {file}')

    @staticmethod
    async def __send_media_groups(media, bot, chat_id):
        """
        Sends media groups with 10 files max in one group.

        Args:
            media (list): Media files.
            bot (Bot): Bot instance.
            chat_id (int): Chat ID.
        """
        for i in range(0, len(media), 10):
            await bot.send_media_group(chat_id=chat_id, media=media)
