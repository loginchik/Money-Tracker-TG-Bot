"""
Package contains scripts that are dedicated to expense operations.
"""

import logging
import datetime as dt
import time

import asyncpg
import asyncpg.pgproto.types
import pandas as pd
import geopandas as gpd
from shapely.geometry.point import Point


async def get_expense_categories(db_connection: asyncpg.Connection) -> list[asyncpg.Record]:
    """
    Gets all expense categories besides untitled.
    :param db_connection: Database connection
    :return: List of records from DB.
    """
    query = '''SELECT id, title_ru, title_en FROM shared.expense_category WHERE id != 1;'''
    categories = await db_connection.fetch(query)
    return categories


async def get_expense_subcategories(category_id: int, db_connection: asyncpg.Connection) -> list[asyncpg.Record]:
    """
    Gets all expense subcategories besides untitled for the defined category_id.
    :param category_id: Category ID.
    :param db_connection: Database connection
    :return: List of records from DB.
    """
    query = f'''SELECT id, title_ru, title_en FROM shared.expense_subcategory WHERE category = {category_id};'''
    subcategories = await db_connection.fetch(query)
    return subcategories


async def add_expense(user_id: int, amount: float, subcategory_id: int, event_time: dt.datetime,
                      location: Point | None, db_connection: asyncpg.Connection) -> bool:
    """
    Saves new expense data to DB.
    :param user_id: User tg_id.
    :param amount: Money amount.
    :param subcategory_id: Subcategory id.
    :param event_time: Event timestamp.
    :param location: Geometry in 4326.
    :param db_connection: Database connection
    """
    async with db_connection.transaction():
        try:
            pg_location = location.wkt if location is not None else None
            query = f'''INSERT INTO user_based.expense_{user_id} 
            (user_id, amount, subcategory, event_time, location) 
            VALUES ($1, $2, $3, $4, $5);'''
            await db_connection.execute(query, user_id, amount, subcategory_id, event_time, pg_location)
            return True
        except Exception as e:
            logging.error(e)
            return False


def raw_data_to_gpd(raw_data) -> gpd.GeoDataFrame:

    df = pd.DataFrame(
        {
            'event_time': [record['event_time'] for record in raw_data],
            'expense_category': [record['expense_category'] for record in raw_data],
            'expense_subcategory': [record['expense_subcategory'] for record in raw_data],
            'amount': [record['amount'] for record in raw_data],
            'location': [record['location'] for record in raw_data]
         }
    )
    df['even_time'] = df['event_time'].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S'))
    df['amount'] = df['amount'].astype(float)
    df['location'] = df['location'].apply(lambda x: Point(x.x, x.y) if x is not None else None)
    gdf = gpd.GeoDataFrame(df, geometry='location', crs=4326)
    return gdf


async def get_user_expenses(user_id: int, user_lang: str, db_connection: asyncpg.Connection) -> gpd.GeoDataFrame | None:
    title_column = 'title_ru' if user_lang == 'ru' else 'title_en'
    try:
        query = f'''select 
            e.event_time, 
            ec.{title_column} as expense_category, 
            es.{title_column} as expense_subcategory, 
            e.amount, 
            e."location"::point 
        from user_based.expense_{user_id} e 
        join shared.expense_subcategory es on es.id = e.subcategory
        join shared.expense_category ec on es.category = ec.id
        where e.user_id = $1;
        '''
        raw_data = await db_connection.fetch(query, user_id)
        data = raw_data_to_gpd(raw_data)
        size_limit = 2000000000
        limit_date = (dt.date(dt.date.today().year, 1, 1))
        while data.__sizeof__() > size_limit:
            query = f'''select e.event_time, ec.{title_column} as expense_category, es.{title_column} as expense_sucategory, 
                    e.amount, e."location" from user_based.expense_{user_id} e 
                    join shared.expense_subcategory es on es.id = e.subcategory
                    join shared.expense_category ec on es.category = ec.id
                    where e.user_id = $1 and e.event_time >= $2;
                    '''
            raw_data = await db_connection.fetch(query, user_id, limit_date)
            data = raw_data_to_gpd(raw_data)
            limit_date = limit_date + dt.timedelta(days=1)
        return data
    except Exception as e:
        logging.error(e)
        return None


async def get_user_expenses_in_daterange(user_id: int, user_lang: str, db_connection: asyncpg.Connection,
                                         start_date: dt.date, end_date: dt.date) -> gpd.GeoDataFrame | None:
    if end_date == dt.date.today():
        end_date = dt.datetime.now()
    title_column = 'title_ru' if user_lang == 'ru' else 'title_en'
    try:
        query = f'''select 
                e.event_time, 
                ec.{title_column} as expense_category, 
                es.{title_column} as expense_subcategory, 
                e.amount, 
                e."location"::point 
            from user_based.expense_{user_id} e 
            join shared.expense_subcategory es on es.id = e.subcategory
            join shared.expense_category ec on es.category = ec.id
            where e.user_id = $1 and e.event_time >= $2 and e.event_time <= $3;
            '''
        raw_data = await db_connection.fetch(query, user_id, start_date, end_date)
        data = raw_data_to_gpd(raw_data)
        return data
    except Exception as e:
        logging.error(e)
        return None
