"""
Package contains scripts that are dedicated to expense limit operations.
"""

import logging
import datetime as dt

from db.connection import create_connection


async def add_expense_limit(user_id: int, period: int, current_period_start: dt.datetime,
                            limit_value: float, end_date: dt.date | None, cumulative: bool,
                            user_title: str, subcategory_id: int) -> bool:
    conn = await create_connection()
    try:
        query = f'''INSERT INTO user_based.expense_limit_{user_id} 
        (user_id, period, current_period_start, limit_value, end_date, cumulative, user_title, subcategory)
        VALUES ($1::int, $2::int2, $3::date, $4::numeric, $5, $6::bool, $7, $8::int2) 
        ON CONFLICT (user_id, user_title) 
        DO UPDATE SET period = $2, current_period_start = $3, limit_value = $4, end_date = $5, cumulative = $6, 
        subcategory = $8::int2;
        '''
        await conn.execute(query, user_id, period, current_period_start, limit_value, end_date, cumulative,
                           user_title, subcategory_id)
        logging.info('Added expense limit')
        return True
    except Exception as e:
        logging.error(e)
        return False
    finally:
        await conn.close()
