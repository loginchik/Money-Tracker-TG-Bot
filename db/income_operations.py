"""
Package contains scripts that are dedicated to income operations.
"""

import datetime as dt
import logging

import asyncpg
import pandas as pd


async def add_income(user_id: int, amount: float | int, passive: bool, event_date: dt.date,
                     db_connection: asyncpg.Connection):
    async with db_connection.transaction():
        try:
            query = '''INSERT INTO user_based.income (user_id, amount, passive, event_date) VALUES ($1, $2, $3, $4);'''
            await db_connection.execute(query, user_id, amount, passive, event_date)
            return True
        except Exception as e:
            logging.error(e)
            return False


def raw_data_to_df(raw_data) -> pd.DataFrame:
    """
    As fas as pandas and geopandas do not support async connection to database, the convertion of db records
    from raw list to dataframe is done in this function.

    :param raw_data: List of raw records.
    :return: Pandas dataframe.
    """
    df = pd.DataFrame(
        {'event_date': [record['event_date'] for record in raw_data],
         'income_type': [record['income_type'] for record in raw_data],
         'amount': [record['amount'] for record in raw_data]
         }
    )
    df['event_date'] = df['event_date'].apply(lambda x: x.strftime('%Y-%m-%d'))
    df['amount'] = df['amount'].astype(float)
    return df


async def get_user_income(user_id: int, db_connection: asyncpg.Connection):
    try:
        query = f'''select i.event_date, cast(
            case when i.passive = 'true' then 'passive'
            else 'active'
            end as varchar
        ) as income_type, 
        i.amount from user_based.income_{user_id} i 
        
        where i.user_id = {user_id};
        '''
        raw_data = await db_connection.fetch(query)
        data = raw_data_to_df(raw_data)
        return data
    except Exception as e:
        logging.error(e)
        return None
