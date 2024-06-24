import os
import json

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from loguru import logger

from .shared_schema import BotUser
from .shared_schema import ExpenseCategory
from .shared_schema import ExpenseSubcategory
from .shared_schema import ExpenseLimitPeriod
from .user_based_schema import Expense
from .user_based_schema import ExpenseLimit
from .user_based_schema import Income
from .shared_schema import setup_shared_schema
from .user_based_schema import setup_user_based_schema
from .connection import database_url
from configs import BASE_DIR


def setup_schemas(test_mode=False, drop_first=False):
    """
    Creates tables in shared and user_based tables, if they do not exists.

    Args:
        test_mode (bool): Should system work with test database or not. Defaults to False.
        drop_first (bool): Should system drop all tables before creating them. Defaults to False.
    """
    setup_engine = create_engine(database_url(async_=False, test=test_mode))
    setup_shared_schema(setup_engine=setup_engine, drop_first=drop_first)
    setup_user_based_schema(setup_engine=setup_engine, drop_first=drop_first)
    setup_engine.dispose()


async def insert_or_update_categories(async_session):
    """
    Opens static categories.json file and updates categories table in accordance with file data.

    If some categories are present in DB but are not present in file, they are ignored.
    No data is being deleted.

    Args:
        async_session (async_sessionmaker[AsyncSession]): async_sessionmaker to request AsyncSession.
    """
    fp = os.path.join(BASE_DIR, 'db', 'static', 'categories.json')
    with open(fp, 'r') as f:
        categories = json.load(f)
    for category_id, category_data in categories.items():
        res = await ExpenseCategory.insert_or_update(category_id=int(category_id), title_ru=category_data['title_ru'],
                                                     title_en=category_data['title_en'], slug=category_data['slug'],
                                                     async_session=async_session)
        if res:
            logger.info(res)


async def insert_or_update_subcategories(async_session):
    """
    Opens static subcategories.json file and updates subcategories table in accordance with file data.

    If some subcategories are present in DB but are not present in file, they are ignored.
    No data is being deleted.

    Args:
        async_session (async_sessionmaker[AsyncSession]): async_sessionmaker to request AsyncSession.
    """
    fp = os.path.join(BASE_DIR, 'db', 'static', 'subcategories.json')
    with open(fp, 'r') as f:
        subcategories = json.load(f)
    for subcategory_id, subcategory_data in subcategories.items():
        res = await ExpenseSubcategory.insert_or_update(subcategory_id=int(subcategory_id),
                                                        title_ru=subcategory_data['title_ru'],
                                                        title_en=subcategory_data['title_en'],
                                                        slug=subcategory_data['slug'],
                                                        category_id=subcategory_data['category_id'],
                                                        async_session=async_session)
        if res:
            logger.info(res)


async def insert_or_update_limit_periods(async_session):
    """
    Opens static limit_periods.json file and updates limit periods table in accordance with file data.

    If some periods are present in DB but are not present in file, they are ignored.
    No data is being deleted.

    Args:
        async_session (async_sessionmaker[AsyncSession]): async_sessionmaker to request AsyncSession.
    """
    fp = os.path.join(BASE_DIR, 'db', 'static', 'limit_periods.json')
    with open(fp, 'r') as f:
        periods = json.load(f)
    for period_id, period_value in periods.items():
        res = await ExpenseLimitPeriod.insert_or_update(period_id=int(period_id), period_value=int(period_value), async_session=async_session)
        if res:
            logger.info(res)


async def insert_or_update_static(async_session):
    """
    Opens static files and updates static tables in shared schema.

    Args:
        async_session (async_sessionmaker[AsyncSession]): async_sessionmaker to request AsyncSession.
    """
    await insert_or_update_categories(async_session)
    await insert_or_update_limit_periods(async_session)
    await insert_or_update_subcategories(async_session)


__all__ = (
    'BotUser', 'ExpenseCategory', 'ExpenseSubcategory', 'ExpenseLimitPeriod',
    'Expense', 'ExpenseLimit', 'Income',
    'setup_schemas', 'insert_or_update_static'
)
