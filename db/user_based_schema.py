import datetime as dt
from decimal import Decimal
from random import randint

from loguru import logger
from sqlalchemy import MetaData
from sqlalchemy.orm import declarative_base
from sqlalchemy import ForeignKey
from sqlalchemy import ARRAY
from sqlalchemy import Column
from sqlalchemy import Sequence
from sqlalchemy import Integer, SmallInteger
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import Boolean
from sqlalchemy import DateTime, Date
from sqlalchemy import select, delete, update
from sqlalchemy.sql import functions

from geoalchemy2 import Geometry
from geoalchemy2.shape import from_shape

import pandas as pd
import geopandas as gpd

from db import BotUser, ExpenseSubcategory, ExpenseCategory, ExpenseLimitPeriod
from configs import scheduler, sync_engine, async_sess_maker


user_based_meta = MetaData(schema='user_based')
UserBasedBase = declarative_base(metadata=user_based_meta)


class Expense(UserBasedBase):
    """
    Expenses table.
    """
    __tablename__ = 'expense'
    __table_args__ = {'extend_existing': True}

    expense_id = Column(Integer, Sequence(name='expense_id_seq', schema='user_based'), primary_key=True, autoincrement=True, nullable=False)
    user_id = Column(Integer, ForeignKey(BotUser.tg_id, ondelete='CASCADE', onupdate='CASCADE', name='expense_user_fk'), comment='Owner user ID', index=True)
    amount = Column(Numeric, nullable=False, comment='Expense amount')
    subcategory = Column(SmallInteger, ForeignKey(ExpenseSubcategory.id, ondelete='SET DEFAULT', onupdate='CASCADE'), nullable=False, default=1)
    event_time = Column(DateTime, nullable=False, default=dt.datetime.now, comment='Payment date and time')
    location = Column(Geometry('POINT', srid=4326), nullable=True, comment='Location coordinates')

    @classmethod
    async def create(cls, user_id, amount, subcategory_id, event_time, location):
        """
        Check input data and saves expense to database, if all values are correct.

        Args:
            user_id (int): User's id. User must be present in DB.
            amount (float): Amount of expense. Must be positive.
            subcategory_id (int): Target subcategory's id. Subcategory with such id must be present in DB.
            event_time (datetime.datetime): Event time. Must be in the past.
            location (str): Location of expense.
        """
        # Check amount
        if amount < 0:
            raise ValueError('Amount must be positive')
        # Check subcategory exists
        subcategory = await ExpenseSubcategory.get_by_id(subcategory_id)
        if subcategory is None:
            raise ValueError('Subcategory with such ID does not exist')
        # Check event time is in the past
        if not isinstance(event_time, dt.datetime):
            raise TypeError('Event time must be datetime.datetime')
        if event_time > dt.datetime.now():
            raise ValueError('Event time must be in the past')

        # Convert location, if present
        if location is not None:
            location = from_shape(location)

        # If all values are correct, create new expense object
        new_expense = cls.__new__(cls)
        new_expense.__init__(user_id=user_id, amount=amount, subcategory=subcategory_id, event_time=event_time,
                             location=location)
        # Save expense to db
        async with async_sess_maker() as session:
            async with session.begin():
                session.add(new_expense)

        # Update relevant expense limits
        await ExpenseLimit.update_balance_after_expense(user_id, event_time, subcategory_id, amount)

    @classmethod
    def select_for_export(cls, user_id, chunk_size=1000, user_lang='ru'):
        """
        Returns generator of geopandas.GeoDataFrame with chunk_size in one chunk.

        Args:
            user_id (int): User's id.
            chunk_size (int): Max records in one chunk.
            user_lang (str): User language.

        Returns:
            gpd.GeoDataFrame: Generator of user expenses.
        """
        if user_lang == 'ru':
            query = (select(cls.event_time, cls.amount, cls.location, ExpenseSubcategory.title_ru, ExpenseCategory.title_ru)
                     .where(user_id == cls.user_id)
                     .join_from(ExpenseSubcategory, cls, ExpenseSubcategory.id == cls.subcategory)
                     .join_from(ExpenseSubcategory, ExpenseCategory, ExpenseSubcategory.category == ExpenseCategory.id)
                     .order_by(cls.event_time.desc()))
        else:
            query = (select(cls.event_time, cls.amount, cls.location,
                            ExpenseSubcategory.title_en, ExpenseCategory.title_en)
                     .where(user_id == cls.user_id)
                     .join_from(ExpenseSubcategory, cls)
                     .order_by(cls.event_time.desc()))

        return gpd.read_postgis(sql=query, con=sync_engine, chunksize=chunk_size, geom_col='location', crs=4326)


class ExpenseLimit(UserBasedBase):
    """
    Expense limits table.
    """

    __tablename__ = 'expense_limit'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, Sequence(name='expense_limit_id_seq', schema='user_based'), primary_key=True, autoincrement=True, nullable=False)
    user_id = Column(Integer, ForeignKey(BotUser.tg_id, ondelete='CASCADE', onupdate='CASCADE', name='expense_limit_user_fk'), nullable=False, comment='Owner user ID', index=True)
    period = Column(SmallInteger, ForeignKey(ExpenseLimitPeriod.id, ondelete='RESTRICT', onupdate='CASCADE', name='expense_limit_period_fk'), nullable=False, comment='Period ID')
    current_period_start = Column(Date, nullable=False, default=dt.date.today, comment='Current period start date')
    current_period_end = Column(Date, nullable=False, comment='Current period end date')
    limit_value = Column(Numeric, nullable=False, comment='Limit value')
    current_balance = Column(Numeric, nullable=False, comment='Current balance', default=limit_value)
    end_date = Column(Date, nullable=True, comment='Limit expiration date')
    cumulative = Column(Boolean, nullable=False, default=False, comment='Cumulative status')
    user_title = Column(String(100), nullable=False, comment='User title')
    subcategories = Column(ARRAY(SmallInteger), nullable=False, comment='Subcategories ids')

    @classmethod
    async def create(cls, user_id, period_id, current_period_start, limit_value, cumulative, user_title, subcategories, end_date=None):
        """
        Check input data and saves expense limit to database, if all values are correct.

        Args:
            user_id (int): User's id. User must be present in DB.
            period_id (int): Period id.
            current_period_start (datetime.date): Current period start date.
            limit_value (float): Limit value of expense.
            end_date (datetime.date): End date of expense.
            cumulative (bool): Cumulative status of expense.
            user_title (str): User's title.
            subcategories (list[int]): Target subcategories' ids.
        """
        # Check the title is unique for the user
        existing_same = await cls.select_by_user_and_title(user_id=user_id, title=user_title)
        if existing_same is not None:
            raise ValueError('Expense limit with such title already exists')

        # Check period is correct and calculate period end date if so
        period = await ExpenseLimitPeriod.get_by_id(period_id)
        if period is not None:
            current_period_end = period.calculate_end_date(start_date=current_period_start)
        else:
            raise ValueError('Period with such id does not exist')

        # Check subcategory exists
        for i in subcategories:
            subcategory = await ExpenseSubcategory.get_by_id(i)
            if subcategory is None:
                raise ValueError('Subcategory with such id does not exist')

        # Query matching expenses to calculate current balance
        if current_period_start <= dt.date.today():
            expenses_query = (select(functions.sum(Expense.amount))
                              .where(user_id == Expense.user_id)
                              .where(Expense.subcategory.in_(subcategories))
                              .where(Expense.event_time >= current_period_start)
                              .where(Expense.event_time <= current_period_end))
            async with async_sess_maker() as session:
                data = await session.execute(expenses_query)

            current_expenses = data.scalar()
            if current_expenses is None:
                current_balance = limit_value
            else:
                current_balance = Decimal.from_float(limit_value) - current_expenses
        else:
            # Future start date means that there are no expenses
            current_balance = limit_value

        # Save object
        limit_ = cls.__new__(cls)
        limit_.__init__(user_id=user_id, period=period_id, current_period_start=current_period_start,
                        current_period_end=current_period_end, limit_value=limit_value,
                        current_balance=current_balance, end_date=end_date, cumulative=cumulative,
                        user_title=user_title, subcategories=subcategories)
        async with async_sess_maker() as session:
            session.add(limit_)
            await session.commit()

        # Add delete task on end date
        if end_date is not None:
            delete_datetime = cls.__calculate_job_dt(date_value=end_date)
            delete_job_id = f'delete_el_{user_id}_{user_title}'
            scheduler.add_job(cls.delete_by_user_id_and_title, trigger='date', replace_existing=True,
                              args=[user_id, user_title], id=delete_job_id,
                              name=f'Delete {user_id} expense limit {user_title} after expiration date',
                              jobstore='default', next_run_time=delete_datetime)
            logger.info(f'Created job {delete_job_id}')

        # Add update task on period end
        next_update_dt = cls.__calculate_job_dt(date_value=current_period_end)
        update_job_id = f'update_el_{user_id}_{user_title}'
        scheduler.add_job(cls.update_balance_for_new_period, trigger='date', replace_existing=True,
                          args=[user_id, user_title], id=update_job_id,
                          name=f'Update balance for {user_id} expense limit {user_title} after period end date',
                          jobstore='default', next_run_time=next_update_dt)
        logger.info(f'Created job {update_job_id}')

    @classmethod
    async def delete_by_user_id_and_title(cls, user_id, user_title):
        """
        Deletes user expense limit by its user id and user specified title.

        Args:
            user_id (int): User's id.
            user_title (str): User title.
        """
        query = delete(cls).where(user_id == cls.user_id).where(user_title == cls.user_title)
        async with async_sess_maker() as session:
            async with session.begin():
                await session.execute(query)
                await session.commit()
        logger.info(f'Deleted {user_id} expense limit {user_title}')

    @classmethod
    async def select_by_user_id(cls, user_id):
        """
        Gets user specified expense limit as this class objects.

        Args:
            user_id (int): User's id. User must be present in DB.

        Returns:
            list[ExpenseLimit]: List of user expense limits.
        """
        query = select(cls).where(user_id == cls.user_id).order_by(cls.current_period_start.desc())
        async with async_sess_maker() as session:
            data = await session.execute(query)
        return data.all()

    @classmethod
    async def select_by_user_and_title(cls, user_id, title):
        """
        Gets one or none expense limit object with specifier user id and user title.

        Args:
            user_id (int): User's id.
            title (str): User title.

        Returns:
            ExpenseLimit | None: Expense limit object.
        """
        query = select(cls).where(user_id == cls.user_id).where(title == cls.user_title)
        async with async_sess_maker() as session:
            data = await session.execute(query)

        result = data.one_or_none()
        return result[0] if result is not None else None

    @classmethod
    async def select_titles(cls, user_id):
        """
        Selects user's expense limit titles.

        Args:
            user_id (int): User's id.

        Returns:
            list[str]: List of user's expense limits' titles.
        """
        query = select(cls.user_title).where(user_id == cls.user_id)
        async with async_sess_maker() as session:
            data = await session.execute(query)
        result = data.all()
        return [res[0] for res in result if res is not None]

    @classmethod
    async def update_balance_after_expense(cls, user_id, event_time, subcategory_id, amount):
        """
        Queries expense limits for the user that are assigned to given subcategory id and subtracts from their current
        balance the amount.

        Args:
            user_id (int): User's id. User must be present in DB.
            event_time (datetime.datetime): Event time. Must be in the past.
            subcategory_id (int): Target subcategory's id.
            amount (float): Amount of expense. Must be positive.
        """
        limits_query = (select(cls).where(user_id == cls.user_id).where(cls.current_period_start <= event_time)
                        .where(cls.current_period_end >= event_time).where(cls.subcategories.any(subcategory_id)))
        async with async_sess_maker() as session:
            data = await session.execute(limits_query)
        result = data.all()
        limits = [res[0] for res in result if res is not None]

        updates = []
        for limit in limits:
            current_balance = limit.current_balance - Decimal.from_float(amount)
            stm = update(cls).where(cls.id == limit.id).values(current_balance=current_balance)
            updates.append(stm)

        async with async_sess_maker() as session:
            for stm in updates:
                await session.execute(stm)
                await session.commit()
            logger.info(f'Updated balance for {len(updates)} expense limits of user {user_id}')

    @classmethod
    async def update_balance_for_new_period(cls, user_id, user_title):
        """

        :param user_id:
        :param user_title:
        :return:
        """
        expense_limit = await cls.select_by_user_and_title(user_id, user_title)

        if expense_limit is not None:
            new_period_start = expense_limit.current_period_end + dt.timedelta(days=1)

            if new_period_start < expense_limit.end_date:
                period = await ExpenseLimitPeriod.get_by_id(expense_limit.period)
                if period is not None:
                    new_period_end = period.calculate_end_date(start_date=new_period_start)

                    if expense_limit.cumulative:
                        new_balance = expense_limit.current_balance + expense_limit.limit_value
                    else:
                        new_balance = expense_limit.limit_value

                    update_stm = (update(cls).where(cls.user_id == user_id).where(cls.user_title == user_title)
                                  .values(current_balance=new_balance,
                                          current_period_start=new_period_start,
                                          current_period_end=new_period_end))
                    async with async_sess_maker() as session:
                        await session.execute(update_stm)
                        await session.commit()
                    logger.info(f'Updated expense limit for user {user_id} title {user_title}:'
                                f'new balance - {new_balance}, '
                                f'new start - {new_period_start.strftime("%d.%m.%Y")}, '
                                f'new end - {new_period_end.strftime("%d.%m.%Y")}')

                    next_update_dt = cls.__calculate_job_dt(date_value=new_period_end)
                    update_job_id = f'update_el_{user_id}_{user_title}'
                    scheduler.add_job(cls.update_balance_for_new_period, trigger='date', replace_existing=True,
                                      args=[user_id, user_title], id=update_job_id,
                                      name=f'Update balance for {user_id} expense limit {user_title} after period end date',
                                      jobstore='default', next_run_time=next_update_dt)
                    logger.info(f'Created job {update_job_id}')

                else:
                    await cls.delete_by_user_id_and_title(user_id, user_title)
            else:
                await cls.delete_by_user_id_and_title(user_id, user_title)

    @staticmethod
    def __calculate_job_dt(date_value):
        """

        :param date_value:
        :return:
        """
        next_day = date_value + dt.timedelta(days=1)
        return dt.datetime(next_day.year, next_day.month, next_day.day, 0, 1, randint(1, 55))


class Income(UserBasedBase):
    """
    Incomes table.
    """
    __tablename__ = 'income'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, Sequence(name='income_id_seq', schema='user_based'), primary_key=True, nullable=False, comment='Income ID')
    user_id = Column(Integer, ForeignKey(BotUser.tg_id, ondelete='CASCADE', onupdate='CASCADE'), nullable=False, comment='User ID', index=True)
    amount = Column(Numeric, nullable=False, comment='Income amount')
    event_date = Column(Date, nullable=False, default=dt.date.today, comment='Income date')
    passive_status = Column(Boolean, nullable=False, default=False, comment='Income is passive status')

    @classmethod
    async def create(cls, user_id, amount, passive, event_date):
        """
        Saves income object to database, if all values are correct.

        Args:
            user_id (int): User's id. User must be present in DB.
            amount (float): Amount of income. Must be positive.
            passive (bool): Whether income is passive or not.
            event_date (date): Event time. Must be in the past.
        """
        # Check amount
        if amount < 0:
            raise ValueError('Amount must be positive')
        # Check event date is in the past
        if not isinstance(event_date, dt.date):
            raise TypeError('Event date must be datetime.date')
        if event_date > dt.datetime.now().date():
            raise ValueError('Event date must be in the past')

        # If all values are correct, create new income object
        income = cls.__new__(cls)
        income.__init__(user_id=user_id, amount=amount, passive_status=passive, event_date=event_date)

        # Save object to DB
        async with async_sess_maker() as session:
            async with session.begin():
                session.add(income)

    @classmethod
    def select_by_user_id(cls, user_id, chunk_size=1000):
        """
        Returns generator of user incomes. Each chunk contains chunk_size records max.

        Cause of pandas limitations, requires synchronous engine to run.

        Args:
            user_id (int): User's id.
            chunk_size (int): Max chunk size.

        Returns:
            Generator[gpd.GeoDataFrame]: Generator of user incomes.
        """
        query = (select(cls.event_date, cls.amount, cls.passive_status)
                 .where(user_id == cls.user_id)
                 .order_by(cls.event_date.desc()))
        return pd.read_sql(sql=query, con=sync_engine, chunksize=chunk_size)


UserBasedBase.metadata.create_all(bind=sync_engine, checkfirst=True)
