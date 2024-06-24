import os
import datetime as dt

from aiogram import Router
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.types import FSInputFile
from aiogram.types import InputMediaDocument
from aiogram.filters import Command, StateFilter

from bot.filters import UserExists
from bot.static.messages import EXPORT_ROUTER_MESSAGES
from bot.fsm_states import ExportStates
from db import Expense, Income


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
        message_text = EXPORT_ROUTER_MESSAGES['not_registered'][user_lang]
        await message.answer(message_text)

    async def export_users_data(self, message, user_lang, state, bot, sync_engine):
        """
        Args:
            message (Message):
            user_lang (str):
            state (FSMContext):
            bot (Bot):
            sync_engine (sqlalchemy.engine.Engine):

        """
        user_id = message.from_user.id
        wait_message_text = EXPORT_ROUTER_MESSAGES['wait'][user_lang]
        await message.answer(wait_message_text)
        await state.set_state(ExportStates.export_expenses)

        try:
            expense_success = await self.export_expenses(message=message, user_id=user_id,
                                                         user_lang=user_lang, bot=bot,
                                                         sync_engine=sync_engine, state=state)
        except Exception as e:
            expense_success = False

        try:
            income_success = await self.export_incomes(message=message, user_id=user_id,
                                                       user_lang=user_lang, bot=bot,
                                                       sync_engine=sync_engine, state=state)
        except Exception as e:
            income_success = False

        if not any([income_success, expense_success]):
            total_error_message_text = EXPORT_ROUTER_MESSAGES['fail'][user_lang]
            await message.answer(total_error_message_text)

    @staticmethod
    async def exporting_expenses_message(message: Message, user_lang: str):
        message_text = EXPORT_ROUTER_MESSAGES['expense_wait'][user_lang]
        await message.answer(message_text)

    @staticmethod
    async def exporting_incomes_message(message: Message, user_lang: str):
        message_text = EXPORT_ROUTER_MESSAGES['income_wait'][user_lang]
        await message.answer(message_text)

    async def export_expenses(self, message, user_id, user_lang, bot, state, sync_engine):
        """

        Args:
            message (Message):
            user_id (int):
            user_lang (str):
            bot (Bot):
            state (FSMContext):
            sync_engine (sqlalchemy.engine.Engine):
        """
        temp_files_csv = []
        temp_files_json = []
        columns = self.expense_data_columns(user_lang=user_lang)
        try:
            # Get expenses data generator
            expenses_data = Expense.select_for_export(user_id=user_id, sync_engine=sync_engine, user_lang=user_lang)
            chunk_id = 0
            for expense_chunk in expenses_data:
                if expense_chunk.shape[0] == 0:
                    raise AttributeError('No expenses data')
                expense_chunk = expense_chunk.rename(columns=columns)
                chunk_id += 1
                exp_temp_filename_gpkg, exp_temp_filename_csv = self.expense_temp_filenames(user_id, chunk_id=chunk_id)
                expense_chunk.to_file(exp_temp_filename_gpkg)
                expense_chunk.to_file(exp_temp_filename_csv, encoding='utf-8', driver='CSV', geometry='AS_WKT')
                temp_files_json.append(exp_temp_filename_gpkg)
                temp_files_csv.append(exp_temp_filename_csv)

            # Collect medias
            input_medias = []
            for i, csv_file, gpkg_file in zip(range(1, chunk_id + 1), temp_files_csv, temp_files_json):
                exp_filename_gpkg, exp_filename_csv = self.expense_out_filenames(chunk_id=i)
                fs_csv = FSInputFile(path=csv_file, filename=exp_filename_csv)
                fs_gpkg = FSInputFile(path=gpkg_file, filename=exp_filename_gpkg)
                input_medias.append(InputMediaDocument(media=fs_csv))
                input_medias.append(InputMediaDocument(media=fs_gpkg))

            # Send medias
            export_expenses_text = EXPORT_ROUTER_MESSAGES['success_expense'][user_lang]
            for i in range(0, len(input_medias), 10):
                medias_chunk = input_medias[i:i + 10]
                await bot.send_media_group(chat_id=message.chat.id, media=medias_chunk)
            await bot.send_message(chat_id=message.chat.id, text=export_expenses_text)
            return True

        except Exception as e:
            print(e)
            error_message = EXPORT_ROUTER_MESSAGES['error_expense'][user_lang]
            await message.answer(error_message)
            return False

        finally:
            # Remove temp files
            for temp_file in temp_files_json + temp_files_csv:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            # Set state on exporting incomes
            await state.set_state(ExportStates.export_incomes)

    async def export_incomes(self, message, user_id, user_lang, bot, state, sync_engine):
        temp_files = []
        columns = self.income_data_columns(user_lang=user_lang)

        try:
            incomes_data = Income.select_by_user_id(user_id=user_id, sync_engine=sync_engine)
            chunk_id = 0
            for income_chunk in incomes_data:
                if income_chunk.shape[0] == 0:
                    raise AttributeError('No incomes data')

                if user_lang == 'ru':
                    income_chunk['passive_status'] = incomes_data['passive_status'].map({True: 'Пассивный', False: 'Активный'})
                else:
                    income_chunk['passive_status'] = incomes_data['passive_status'].map({True: 'Passive', False: 'Active'})
                income_chunk = income_chunk.rename(columns=columns)

                chunk_id += 1
                income_temp_filename = f'{user_id}_{dt.datetime.now().strftime("%d%H%M%S")}_expenses_{chunk_id}.csv'
                income_chunk.to_csv(income_temp_filename)
                temp_files.append(income_temp_filename)

            input_medias = []
            for i, csv_file in zip(range(chunk_id), temp_files):
                income_out_filename = f'{dt.datetime.now().strftime("%d_%m_%Y_%H_%M_%S")}_incomes_{i}.csv'
                fs = FSInputFile(path=csv_file, filename=income_out_filename)
                input_medias.append(InputMediaDocument(media=fs))

            for i in range(0, len(input_medias), 10):
                medias_chunk = input_medias[i:i + 10]
                await bot.send_media_group(chat_id=message.chat.id, media=medias_chunk)
            export_incomes_text = EXPORT_ROUTER_MESSAGES['success_income'][user_lang]
            await message.answer(export_incomes_text)
            return True

        except Exception as e:
            error_message = EXPORT_ROUTER_MESSAGES['error_income'][user_lang]
            await message.answer(error_message)
            return False

        finally:
            # Remove temp file
            for file in temp_files:
                if os.path.exists(file):
                    os.remove(file)
            # Clear the state
            await state.clear()

    @staticmethod
    def expense_temp_filenames(user_id: int, chunk_id) -> tuple[str, str]:
        exp_temp_filename = f'{user_id}_{dt.datetime.now().strftime("%d%H%M%S")}_expenses_{chunk_id}'
        exp_temp_filename_gpkg = exp_temp_filename + '.gpkg'
        exp_temp_filename_csv = exp_temp_filename + '.csv'
        return exp_temp_filename_gpkg, exp_temp_filename_csv

    @staticmethod
    def expense_out_filenames(chunk_id) -> tuple[str, str]:
        out_filename = f'{dt.datetime.now().strftime("%d_%m_%Y_%H_%M_%S")}_expenses_{chunk_id}'
        exp_filename_csv = out_filename + '.csv'
        exp_filename_gpkg = out_filename + '.gpkg'
        return exp_filename_gpkg, exp_filename_csv

    @staticmethod
    def expense_data_columns(user_lang):
        return {
            'event_time': 'Дата платежа',
            'amount': 'Сумма',
            'location': 'Местоположение',
            'title_ru': 'Подкатегория расходов',
            'title_ru_1': 'Категория расходов'
        } if user_lang == 'ru' else {
            'event_time': 'Payment date',
            'amount': 'Money amount',
            'location': 'Location',
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