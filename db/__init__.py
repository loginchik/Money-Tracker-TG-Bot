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

from configs import BASE_DIR


async def insert_or_update_categories():
    """
    Opens static categories.json file and updates categories table in accordance with file data.

    If some categories are present in DB but are not present in file, they are ignored. No data is being deleted.
    """
    fp = os.path.join(BASE_DIR, 'db', 'static', 'categories.json')
    with open(fp, 'r') as f:
        categories = json.load(f)
    for category_id, category_data in categories.items():
        res = await ExpenseCategory.insert_or_update(category_id=int(category_id), title_ru=category_data['title_ru'],
                                                     title_en=category_data['title_en'], slug=category_data['slug'])
        if res:
            logger.info(res)


async def insert_or_update_subcategories():
    """
    Opens static subcategories.json file and updates subcategories table in accordance with file data.

    If some subcategories are present in DB but are not present in file, they are ignored. No data is being deleted.
    """
    fp = os.path.join(BASE_DIR, 'db', 'static', 'subcategories.json')
    with open(fp, 'r') as f:
        subcategories = json.load(f)
    for subcategory_id, subcategory_data in subcategories.items():
        res = await ExpenseSubcategory.insert_or_update(subcategory_id=int(subcategory_id),
                                                        title_ru=subcategory_data['title_ru'],
                                                        title_en=subcategory_data['title_en'],
                                                        slug=subcategory_data['slug'],
                                                        category_id=subcategory_data['category_id'])
        if res:
            logger.info(res)


async def insert_or_update_limit_periods():
    """
    Opens static limit_periods.json file and updates limit periods table in accordance with file data.

    If some periods are present in DB but are not present in file, they are ignored. No data is being deleted.
    """
    fp = os.path.join(BASE_DIR, 'db', 'static', 'limit_periods.json')
    with open(fp, 'r') as f:
        periods = json.load(f)
    for period_id, period_value in periods.items():
        res = await ExpenseLimitPeriod.insert_or_update(period_id=int(period_id), period_value=int(period_value))
        if res:
            logger.info(res)


async def insert_or_update_static():
    """
    Opens static files and updates static tables in shared schema.
    """
    await insert_or_update_categories()
    await insert_or_update_limit_periods()
    await insert_or_update_subcategories()


__all__ = (
    'BotUser', 'ExpenseCategory', 'ExpenseSubcategory', 'ExpenseLimitPeriod',
    'Expense', 'ExpenseLimit', 'Income', 'insert_or_update_static'
)
