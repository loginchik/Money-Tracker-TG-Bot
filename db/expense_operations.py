"""
Package contains scripts that are dedicated to expense operations.
"""

import logging
import datetime as dt

import asyncpg
from shapely.geometry.point import Point

from db.connection import create_connection


async def get_expense_categories() -> list[asyncpg.Record]:
    """
    Gets all expense categories besides untitled.
    :return: List of records from DB.
    """
    conn = await create_connection()
    query = '''SELECT id, title_ru, title_en FROM shared.expense_category WHERE id != 1;'''
    categories = await conn.fetch(query)
    await conn.close()
    return categories


async def get_expense_subcategories(category_id: int) -> list[asyncpg.Record]:
    """
    Gets all expense subcategories besides untitled for the defined category_id.
    :param category_id: Category ID.
    :return: List of records from DB.
    """
    conn = await create_connection()
    query = f'''SELECT id, title_ru, title_en FROM shared.expense_subcategory WHERE category = {category_id};'''
    subcategories = await conn.fetch(query)
    await conn.close()
    return subcategories


async def add_expense(user_id: int, amount: float, subcategory_id: int, event_time: dt.datetime,
                      location: Point | None) -> bool:
    """
    Saves new expense data to DB.
    :param user_id: User tg_id.
    :param amount: Money amount.
    :param subcategory_id: Subcategory id.
    :param event_time: Event timestamp.
    :param location: Geometry in 4326.
    """
    conn = await create_connection()
    try:
        pg_location = location.wkt if location is not None else None
        query = f'''INSERT INTO user_based.expense_{user_id} 
        (user_id, amount, subcategory, event_time, location) 
        VALUES ($1, $2, $3, $4, $5);'''
        await conn.execute(query, user_id, amount, subcategory_id, event_time, pg_location)
        return True
    except Exception as e:
        logging.error(e)
        return False
    finally:
        await conn.close()
