"""
Package contains scripts that are dedicated to user operations, such as creating or deleting
user record in table and all partition tables required.
"""

import logging

import asyncpg

from db.connection import create_connection


async def user_exists(user_id: int, connection: asyncpg.Connection) -> bool:
    """
    Check if a user exists in database table of bot users.
    :param user_id: TG user ID.
    :param connection: DB connection.
    :return: Exists status.
    """
    # User is in users table
    users_table_query = 'SELECT EXISTS (SELECT tg_id FROM shared.user WHERE tg_id = $1);'
    exists = await connection.fetchval(users_table_query, user_id)
    # User expenses table exists
    table_query = '''SELECT EXISTS (SELECT FROM information_schema.tables 
    WHERE table_schema = $1 AND table_name = $2);'''
    expense_table_exists = await connection.fetchval(table_query, 'user_based', f'expense_{user_id}')
    # User incomes table exists
    income_table_exists = await connection.fetchval(table_query, 'user_based', f'income_{user_id}')
    # User expense limits table exists
    limits_table_exists = await connection.fetchval(table_query, 'user_based', f'expense_limit_{user_id}')

    return all([exists, expense_table_exists, income_table_exists, limits_table_exists])


async def create_user(**user_data: dict) -> bool:
    """
    Creates user in db if user does not exist, else updates info.
    :param user_data: Dict[tg_id, tg_username, tg_first_name].
    """
    result = True
    db_connection = await create_connection()
    user_tg_id = user_data['tg_id']

    # Create user row in users table
    try:
        create_user_query = '''INSERT INTO shared.user (tg_id, tg_username, tg_first_name, lang) 
        VALUES ($1, $2, $3, $4) 
        ON CONFLICT (tg_id) DO UPDATE SET tg_username = $2, tg_first_name = $3, lang = $4;'''
        await db_connection.execute(create_user_query,user_tg_id, user_data['tg_username'],
                                    user_data['tg_first_name'], user_data['lang'])
        logging.info(f'User {user_tg_id} created')
    except Exception as e:
        logging.critical(e)
        result = False

    # Create partition table in expense table
    try:
        create_expense_partition_query = f'''CREATE TABLE IF NOT EXISTS user_based.expense_{user_tg_id}
        PARTITION OF user_based.expense FOR VALUES IN ('{user_tg_id}');
        '''
        await db_connection.execute(create_expense_partition_query)
        logging.info(f'User {user_tg_id} partition in expense table created')
    except Exception as e:
        logging.critical(e)
        result = False

    # Create partition table in income table
    try:
        create_income_partition_query = f'''CREATE TABLE IF NOT EXISTS user_based.income_{user_tg_id}
        PARTITION OF user_based.income FOR VALUES IN ('{user_tg_id}');
        '''
        await db_connection.execute(create_income_partition_query)
        logging.info(f'User {user_tg_id} partition in income table created')
    except Exception as e:
        logging.critical(e)
        result = False

    # Create partition table in expense limit table
    try:
        create_expense_limit_partition_query = f'''CREATE TABLE IF NOT EXISTS user_based.expense_limit_{user_tg_id}
        PARTITION OF user_based.expense_limit FOR VALUES IN ('{user_tg_id}');
        '''
        await db_connection.execute(create_expense_limit_partition_query)
        logging.info(f'User {user_tg_id} partition in expense_limit table created')
    except Exception as e:
        logging.critical(e)
        result = False

    await db_connection.close()
    return result


async def delete_user_data(user_id: int, db_connection: asyncpg.Connection) -> bool:
    async with db_connection.transaction():
        try:
            delete_user_query = '''DELETE FROM shared.user WHERE tg_id = $1;'''
            await db_connection.execute(delete_user_query, user_id)
            delete_user_expense_partition = f'DROP TABLE IF EXISTS user_based.expense_{user_id};'
            await db_connection.execute(delete_user_expense_partition)
            delete_user_income_partition = f'DROP TABLE IF EXISTS user_based.income_{user_id};'
            await db_connection.execute(delete_user_income_partition)

            return True

        except Exception as e:
            logging.error(e)
            return False
