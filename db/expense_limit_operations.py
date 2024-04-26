"""
Package contains scripts that are dedicated to expense limit operations.
"""

import logging
import datetime as dt

import asyncpg
import pandas as pd

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


async def user_expense_limits_info(user_id: int, db_connection: asyncpg.Connection,
                                   user_lang: str) -> pd.DataFrame | None:
    title_column = 'title_ru' if user_lang == 'ru' else 'title_en'
    query = f'''SELECT el.user_title, ec.{title_column} as category, es.{title_column} as subcategory, 
    el.current_period_start::date, el.current_period_end::date, 
    el.current_balance, el.limit_value, el.end_date::date, el.cumulative
    from user_based.expense_limit_{user_id} el
    join shared.expense_subcategory es on es.id = el.subcategory
    join shared.expense_category ec on es.category = ec.id;'''
    try:
        stats = await db_connection.fetch(query)
        df = pd.DataFrame({
            'title': [record['user_title'] for record in stats],
            'category': [record['category'] for record in stats],
            'subcategory': [record['subcategory'] for record in stats],
            'period_start': [record['current_period_start'] for record in stats],
            'period_end': [record['current_period_end'] for record in stats],
            'total_end': [record['end_date'] for record in stats],
            'balance': [record['current_balance'] for record in stats],
            'limit': [record['limit_value'] for record in stats],
            'cumulative': [record['cumulative'] for record in stats],
        })
        return df
    except Exception as e:
        logging.error(e)
        return None


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


async def delete_expense_limit(user_id: int, user_title: str, db_connection: asyncpg.Connection) -> bool:
    """
    Deletes expense limit associated with given user id and user title from database.
    :param user_id: User telegram id.
    :param user_title: User expense limit title.
    :param db_connection: Database connection.
    :return: Success or failure.
    """
    async with db_connection.transaction():
        try:
            await db_connection.execute(f'''DELETE FROM user_based.expense_limit_{user_id} el
            WHERE el.user_title = $1;''', user_title)
            return True
        except Exception as e:
            logging.error(e)
            return False
