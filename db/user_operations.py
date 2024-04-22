import asyncpg

from db.connection import create_connection


async def user_exists(user_id: int, connection: asyncpg.Connection) -> bool:
    """
    Check if a user exists in database table of bot users.
    :param user_id: TG user ID.
    :param connection: DB connection.
    :return: Exists status.
    """
    query = 'SELECT EXISTS (SELECT tg_id FROM shared.user WHERE tg_id = $1);'
    exists = await connection.fetchval(query, user_id)
    return exists


async def create_user(**user_data: dict) -> None:
    """
    Creates user in db if user does not exist, else updates info.
    :param user_data: Dict[tg_id, tg_username, tg_first_name].
    """
    db_connection = await create_connection()
    query = '''INSERT INTO shared.user (tg_id, tg_username, tg_first_name) 
    VALUES ($1, $2, $3) 
    ON CONFLICT (tg_id) DO UPDATE SET tg_username = $2, tg_first_name = $3;'''
    await db_connection.execute(query,user_data['tg_id'], user_data['tg_username'], user_data['tg_first_name'])
    await db_connection.close()

