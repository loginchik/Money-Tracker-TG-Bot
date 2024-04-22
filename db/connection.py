import os

import asyncpg
from dotenv import dotenv_values


def database_url() -> str:
    """
    Get database URL from environment variables.
    :return: DB URL.
    """
    secrets_path = os.path.abspath('db/.env')
    secrets = dotenv_values(secrets_path)
    user_password = f'{secrets["DB_USER"]}:{secrets["DB_PASSWORD"]}'
    host_port_dbname = f'{secrets["DB_HOST"]}:{secrets["DB_PORT"]}/{secrets["DB_NAME"]}'
    db_url = f'postgresql://{user_password}@{host_port_dbname}'
    return db_url


async def create_connection() -> asyncpg.Connection:
    """
    Creates database connection.
    :return: Async connection to DB.
    """

    db_url = database_url()
    connection = await asyncpg.connect(dsn=db_url)
    return connection
