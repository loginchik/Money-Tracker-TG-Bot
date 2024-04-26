"""
Package contains scripts that are dedicated to expense limit operations.
"""

import logging
import datetime as dt

import asyncpg

from bot.static.messages import NEW_ROUTER_MESSAGES


async def add_expense_limit(user_id: int, period: int, current_period_start: dt.datetime,
                            limit_value: float, end_date: dt.date | None, cumulative: bool,
                            user_title: str, subcategory_id: int, db_connection: asyncpg.Connection) -> bool:
    async with db_connection.transaction():
        try:
            query = f'''INSERT INTO user_based.expense_limit_{user_id} 
            (user_id, period, current_period_start, limit_value, end_date, cumulative, user_title, subcategory)
            VALUES ($1::int, $2::int2, $3::date, $4::numeric, $5, $6::bool, $7, $8::int2) 
            ON CONFLICT (user_id, user_title) 
            DO UPDATE SET period = $2, current_period_start = $3, limit_value = $4, end_date = $5, cumulative = $6, 
            subcategory = $8::int2;
            '''
            await db_connection.execute(query, user_id, period, current_period_start, limit_value, end_date, cumulative,
                                        user_title, subcategory_id)
            logging.info('Added expense limit')
            return True
        except Exception as e:
            logging.error(e)
            return False


async def user_expense_limits(user_id: int, db_connection: asyncpg.Connection):
    query = f'''SELECT user_title FROM user_based.expense_limit_{user_id};'''
    try:
        titles = await db_connection.fetch(query)
        return [t['user_title'] for t in titles]
    except Exception as e:
        logging.error(e)
        return []


async def subcategory_expense_limit_stats(subcategory_id: int, user_id: int, user_lang: str,
                                          db_connection: asyncpg.Connection):
    query = f'''SELECT user_title, current_period_end::date, current_balance, limit_value 
    from user_based.expense_limit_{user_id} where subcategory = $1;'''
    try:
        stats = await db_connection.fetch(query, subcategory_id)
        stats_texts = []
        for stat in stats:
            original_text = NEW_ROUTER_MESSAGES['expense_limit_stats'][user_lang]
            days_until_finish = (dt.date.today() - stat['current_period_end']).days
            limit_value = stat['limit_value']
            current_balance = stat['current_balance']
            if current_balance < 0:
                progress = 100
                progress_bar = '#' * 20
            else:
                progress = round((current_balance / limit_value) * 100)
                progress_short = round(progress / 5)
                progress_bar = '#' * progress_short + '-' * (20 - progress_short)
            formatted = original_text.format(stat['user_title'], str(abs(days_until_finish)), progress_bar,
                                             str(progress), str(current_balance))
            stats_texts.append(formatted)
        return '\n\n'.join(stats_texts)
    except Exception as e:
        logging.error(e)
        return None

