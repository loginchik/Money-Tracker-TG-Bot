"""
Package contains scripts that are dedicated to expense operations.
"""

import logging
import datetime as dt

import asyncpg
import asyncpg.pgproto.types
import pandas as pd
import geopandas as gpd
from shapely.geometry.point import Point

from db.connection import create_connection, create_sync_connection


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


def raw_data_to_gpd(raw_data) -> gpd.GeoDataFrame:
    times = []
    categories = []
    subcategories = []
    amounts = []
    locations = []
    for record in raw_data:
        times.append(record['event_time'])
        categories.append(record['expense_category'])
        subcategories.append(record['expense_subcategory'])
        amounts.append(record['amount'])
        locations.append(record['location'])

    df = pd.DataFrame(
        {
            'event_time': times,
            'expense_category': categories,
            'expense_subcategory': subcategories,
            'amount': amounts,
            'location': locations
         }
    )
    df['even_time'] = df['event_time'].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S'))
    df['amount'] = df['amount'].astype(float)
    df['location'] = df['location'].apply(lambda x: Point(x.x, x.y) if x is not None else None)
    gdf = gpd.GeoDataFrame(df, geometry='location', crs=4326)
    return gdf


async def get_user_expenses(user_id: int, user_lang: str) -> gpd.GeoDataFrame | None:
    conn = await create_connection()
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
        raw_data = await conn.fetch(query, user_id)
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
            raw_data = await conn.fetch(query, user_id, limit_date)
            data = raw_data_to_gpd(raw_data)
            limit_date = limit_date + dt.timedelta(days=1)
        return data
    except Exception as e:
        logging.error(e)
        return None
    finally:
        await conn.close()
