import asyncpg


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
