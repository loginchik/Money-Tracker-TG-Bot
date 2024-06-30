import os
import datetime as dt
from loguru import logger

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.types.input_file import FSInputFile
from aiogram.types import InputMediaPhoto
from aiogram.filters import Command, StateFilter
from sqlalchemy import select
from sqlalchemy.sql import functions

import geopandas as gpd
import pandas as pd

from bot.filters import UserExists
import bot.keyboards as keyboards
from bot.routers import CommonRouter, MessageTexts as MT
from db import BotUser, Expense, ExpenseLimit, Income, ExpenseSubcategory, ExpenseCategory
from bot.internal.graphs import GraphCreator
from configs import async_sess_maker


class StatsRouter(Router, CommonRouter):
    def __init__(self):
        super().__init__()
        self.name = 'StatsRouter'
        self.register_handlers()

        self.MAIN_COLOR = '#4a08ff'
        self.MAIN_COLOR_RGB = (75, 10, 255)
        self.LIGHT_COLOR = '#cbcaff'
        self.FONT_SIZE = 12

    def register_handlers(self):
        self.message.register(self.no_stats, Command(commands=['stats']), ~UserExists(), StateFilter(None))
        self.message.register(self.stats_choice, Command(commands=['stats']), UserExists(), StateFilter(None))

        self.callback_query.register(self.profile_stats, F.data == 'statistics_profile', UserExists(), StateFilter(None))
        self.callback_query.register(self.expense_limits_stats, F.data == 'statistics_expense_limits', UserExists(), StateFilter(None))
        self.callback_query.register(self.last_month_expenses_stats, F.data == 'statistics_last_month_expense', UserExists(), StateFilter(None))
        self.callback_query.register(self.last_year_income_stats, F.data == 'statistics_last_year_income', UserExists(), StateFilter(None))


    @staticmethod
    async def no_stats(message, user_lang):
        """
            Sends a message with no statistics.

            Args:
                message (Message): Message to send.
                user_lang (str): Language of the message.

            Returns:
                Message: Sent message.
            """
        m_texts = MT('Вы не зарегистрированы, поэтому нет статистики, которую можно было бы показать',
                     'You are not registered. There is no statistics to show')
        return await message.answer(m_texts.get(user_lang))

    @staticmethod
    async def stats_choice(message, user_lang):
        """
        Sends a keyboard with stat options.

        Args:
            message (Message): User message.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        buttons = (
            ('Профиль', 'Profile', 'statistics_profile'),
            ('Пределы расходов', 'Expense limits', 'statistics_expense_limits'),
            ('Расходы за последний месяц', 'Last month expenses', 'statistics_last_month_expense'),
            ('Доходы за последний год', 'Last year incomes', 'statistics_last_year_income')
        )
        keyboard = keyboards.multi_button_keyboard(user_lang, buttons_data=buttons, one_row_count=1)

        m_texts = MT('Выберите, какую статистику вы хотите', 'Choose the statistics to get')
        return await message.answer(m_texts.get(user_lang), reply_markup=keyboard)

    @staticmethod
    async def profile_stats(callback, user_lang):
        """
        Sends user's profile statistics.

        Args:
            callback (CallbackQuery): Callback button.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        user = await BotUser.get_by_id(user_id=callback.from_user.id)
        days_of_usage = (dt.date.today() - user.registration_date).days + 1

        # Basic user info
        message_texts = [
            [
                f'{"Дата регистрации" if user_lang == "ru" else "Registration date"}: {MT.format_date(user.registration_date)}',
                f'{"Дней использования" if user_lang == "ru" else "Days of usage"}: {days_of_usage}'
            ]
        ]

        # General expenses stats
        expenses_query = select(functions.sum(Expense.amount), functions.count(Expense.expense_id)).where(user.tg_id == Expense.user_id)
        async with async_sess_maker() as session:
            data = await session.execute(expenses_query)
        no_expenses = [f'{"Пока не учтено ни одного расхода" if user_lang == "ru" else "No expenses logged yet"}']
        try:
            expenses_sum, expenses_count = list(data.all())[0]
        except (TypeError, IndexError) as e:
            logger.warning(e)
            message_texts.append(no_expenses)
        else:
            if expenses_count == 0:
                message_texts.append(no_expenses)
            else:
                message_texts.append([
                    f'{"Расходов учтено" if user_lang == "ru" else "Expenses logged"}: {expenses_count}',
                    f'{"Общая сумма" if user_lang == "ru" else "Total amount"}: {MT.format_float(expenses_sum)}'
                ])

        # General incomes stats
        incomes_query = select(functions.sum(Income.amount), functions.count(Income.id)).where(user.tg_id == Income.user_id)
        async with async_sess_maker() as session:
            data = await session.execute(incomes_query)
        no_incomes = [f'{"Пока не учтено ни одного дохода" if user_lang == "ru" else "No incomes logged yet"}']
        try:
            incomes_sum, incomes_count = list(data.all())[0]
        except (TypeError, IndexError) as e:
            logger.warning(e)
            message_texts.append(no_incomes)
        else:
            if incomes_count == 0:
                message_texts.append(no_incomes)
            else:
                message_texts.append([
                    f'{"Доходов учтено" if user_lang == "ru" else "Incomes logged"}: {incomes_count}',
                    f'{"Общая сумма" if user_lang == "ru" else "Total amount"}: {MT.format_float(incomes_sum)}'
                ])

        return await callback.message.answer('\n\n'.join(['\n'.join(mt) for mt in message_texts]))

    @staticmethod
    async def expense_limits_stats(callback, user_lang):
        """
        Sends user's expense limits statistics.

        Args:
            callback (CallbackQuery): Callback button.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        # Gather all expense limits linked to the user
        user_limits = await ExpenseLimit.select_by_user_id(user_id=callback.from_user.id)
        # User has no limits
        if len(user_limits) == 0:
            return await callback.message.answer(f'У вас нет пределов расходов' if user_lang == 'ru' else 'You have no expense limits')
        # User has limits
        else:
            reports = []
            # Unpack tuples
            user_limits: list[ExpenseLimit] = [ul[0] for ul in user_limits]
            # Generate report for each of the limits
            for limit in user_limits:
                balance_relation = max(min(limit.current_balance / limit.limit_value, 1), 0)
                period_title = "Текущий период" if user_lang == "ru" else "Current period"
                period_val = f'{MT.format_date(limit.current_period_start)}-{MT.format_date(limit.current_period_end)}'
                p_bar_positive = f'{"+" * round(balance_relation * 20)}'
                p_bar_negative = f'{"-" * (20 - round(balance_relation * 20))}'
                p_bar_descr = f'{MT.format_float(limit.current_balance)} / {MT.format_float(limit.limit_value)}'

                subcategories = []
                lang_attribute = f'title_{user_lang}'
                for subcategory_id in limit.subcategories:
                    subcat = await ExpenseSubcategory.get_by_id(subcategory_id)
                    if subcat is not None:
                        subcategories.append(subcat.__getattribute__(lang_attribute))

                report = [
                    f'<b>{limit.user_title}</b>',
                    f'{", ".join(subcategories)}',
                    f'{period_title}: {period_val}',
                    f'|{p_bar_positive}{p_bar_negative}| ({p_bar_descr})'
                ]

                if limit.cumulative:
                    report.append('Кумулятивный баланс' if user_lang == 'ru' else 'Cumulative')
                if limit.end_date is not None:
                    label = 'Действует до' if user_lang == 'ru' else 'Valid until'
                    report.append(f'{label}: {MT.format_date(limit.end_date)}')
                else:
                    report.append('Бессрочный' if user_lang == 'ru' else 'Endless')

                report_text = '\n'.join(report)
                reports.append(report_text)

            return await callback.message.answer('\n\n'.join(reports))

    async def last_month_expenses_stats(self, callback, user_lang, sync_engine, bot):
        """
        Sends user's last month expense statistics.

        Args:
            callback (CallbackQuery): Callback button.
            user_lang (str): User language.
            sync_engine (SyncEngine): Async engine.
            bot (Bot): Bot instance.

        Returns:
            Message: Reply message.
        """
        # Get date limit and query
        min_date, expenses_query = self.__expense_query_30(user_lang)
        # Query data
        data = gpd.read_postgis(sql=expenses_query, con=sync_engine, geom_col='location')
        # User has no data
        if data.shape[0] == 0:
            m_text = MT('За последние 30 дней у вас нет расходов', 'You have no expenses in last 30 days')
            return await callback.answer(m_text.get(user_lang))

        # User has data. Rename columns to unify scenario
        data = data.rename(columns={
            'title_ru': 'subcategory', 'title_ru_1': 'category',
            'title_en': 'subcategory', 'title_en_1': 'category',
        })

        # Get graphs
        graph_creator = GraphCreator(data=data, user_lang=user_lang)
        paths = graph_creator.create_expense_cards(user_id=callback.from_user.id, min_date=min_date,
                                                   user_nickname=callback.from_user.username)

        message = await self.send_media_group(paths=paths, bot=bot, chat_id=callback.message.chat.id,
                                              message_id=callback.message.message_id)
        await self.send_total_caption(message, user_lang, data.amount.sum())
        self.__clear_files(paths)

    async def last_year_income_stats(self, callback, user_lang, sync_engine, bot):
        """
        Sends user's last year income statistics

        Args:
            callback (CallbackQuery): Callback button.
            user_lang (str): User language.
            sync_engine (SyncEngine): Async engine.
            bot (Bot): Bot instance.

        Returns:
            Message: Reply message.
        """
        min_date = dt.date.today() - dt.timedelta(days=365)
        query = select(Income).where(callback.from_user.id == Income.user_id).where(Income.event_date >= min_date)
        data = pd.read_sql(query, con=sync_engine)
        if data.shape[0] == 0:
            m_text = MT('За последние 365 дней у вас нет доходов', 'You have no incomes in last 365 days')
            return await callback.message.answer(m_text.get(user_lang))

        graphs_creator = GraphCreator(data=data, user_lang=user_lang)
        paths = graphs_creator.create_income_cards(user_id=callback.from_user.id, min_date=min_date,
                                                   user_nickname=callback.from_user.username)
        if isinstance(paths, str):
            paths = tuple([paths])

        message = await self.send_media_group(paths=paths, bot=bot, chat_id=callback.message.chat.id,
                                              message_id=callback.message.message_id)
        await self.send_total_caption(message, user_lang, data.amount.sum())
        self.__clear_files(paths)

    @staticmethod
    def __expense_query_30(user_lang):
        """
        Calculates min date (current date - 30 days) and generates expenses data query according to user language.

        Args:
            user_lang (str): User language.

        Returns:
            tuple[datetime.date, sqlalchemy.Select]: Min date value and query object.
        """
        min_date = dt.date.today() - dt.timedelta(days=30)
        # Columns list depends on user language
        columns = (
            Expense.expense_id, Expense.amount, Expense.event_time, Expense.location,
            ExpenseSubcategory.title_ru if user_lang == 'ru' else ExpenseSubcategory.title_en,
            ExpenseCategory.title_ru if user_lang == 'ru' else ExpenseCategory.title_en
        )
        # Query is the same for all languages
        expenses_query = (select(*columns).where(Expense.event_time >= min_date)
                          .join_from(Expense, ExpenseSubcategory,
                                     onclause=Expense.subcategory == ExpenseSubcategory.id)
                          .join_from(ExpenseSubcategory, ExpenseCategory,
                                     onclause=ExpenseCategory.id == ExpenseSubcategory.category))

        return min_date, expenses_query

    @staticmethod
    async def send_media_group(paths, bot, chat_id, message_id):
        """
        Sends files with provided paths to provided chat.

        Args:
            paths (tuple[str]): List of paths.
            bot (Bot): Bot instance.
            chat_id (int): Chat ID.
            message_id (int): Reply to message id.

        Returns:
            Message: Reply message.
        """
        # Send graphs to user
        media_files = []
        for i, path in enumerate(paths):
            media = FSInputFile(path=path, filename=f'graph_{i}.png')
            input_media = InputMediaPhoto(media=media)
            media_files.append(input_media)

        message = await bot.send_media_group(chat_id=chat_id, media=media_files, reply_to_message_id=message_id)
        return message

    @staticmethod
    async def send_total_caption(message, user_lang, total):
        """
        Sends total in reply to message.

        Args:
            message (Message): Reply message.
            user_lang (str): User language.
            total (float): Total amount.

        Returns:
            Message: Reply message.
        """
        caption_text = ': '.join(['Всего' if user_lang == 'ru' else 'Total', MT.format_float(total)])
        return await message[0].reply(text=caption_text)

    @staticmethod
    def __clear_files(paths):
        """
        Deletes files in provided paths.

        Args:
            paths (tuple[str]): List of paths.
        """
        for path in paths:
            if os.path.exists(path) and os.path.isfile(path):
                logger.info(f'Removed {path}')
                os.remove(path)
