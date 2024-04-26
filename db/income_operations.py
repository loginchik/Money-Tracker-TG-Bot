"""
Package contains scripts that are dedicated to income operations.
"""

import datetime as dt
import logging

import pandas as pd

from db.connection import create_connection


async def add_income(user_id: int, amount: float | int, passive: bool, event_date: dt.date):
    connection = await create_connection()
    try:
        query = '''INSERT INTO user_based.income (user_id, amount, passive, event_date) VALUES ($1, $2, $3, $4);'''
        await connection.execute(query, user_id, amount, passive, event_date)
        return True
    except Exception as e:
        logging.error(e)
        return False
    finally:
        await connection.close()


def raw_data_to_df(raw_data) -> pd.DataFrame:
    dates = []
    types = []
    amounts = []
    for record in raw_data:
        dates.append(record['event_date'])
        types.append(record['income_type'])
        amounts.append(record['amount'])

    df = pd.DataFrame({'event_date': dates, 'income_type': types, 'amount': amounts})
    df['event_date'] = df['event_date'].apply(lambda x: x.strftime('%Y-%m-%d'))
    df['amount'] = df['amount'].astype(float)
    return df


async def get_user_income(user_id: int):
    connection = await create_connection()
    try:
        query = f'''select i.event_date, cast(
            case when i.passive = 'true' then 'passive'
            else 'active'
            end as varchar
        ) as income_type, 
        i.amount from user_based.income_{user_id} i 
        
        where i.user_id = {user_id};
        '''
        raw_data = await connection.fetch(query)
        data = raw_data_to_df(raw_data)
        return data
    except Exception as e:
        logging.error(e)
        return None
    finally:
        await connection.close()
