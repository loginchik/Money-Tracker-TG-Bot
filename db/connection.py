"""
Package contains scripts that create connection to the database. Main function for export and
external use is ``create_connection``.
"""

import asyncpg
from settings import db_secrets


def database_url() -> str:
    """
    Get database URL from environment variables.
    :return: DB URL.
    """
    user_password = f'{db_secrets["DB_USER"]}:{db_secrets["DB_PASSWORD"]}'
    host_port_dbname = f'{db_secrets["DB_HOST"]}:{db_secrets["DB_PORT"]}/{db_secrets["DB_NAME"]}'
    db_url = f'postgresql://{user_password}@{host_port_dbname}'
    return db_url


class DBPoolGenerator:
    def __init__(self):
        self.pool = None

    async def __call__(self):
        if self.pool is None:
            self.pool = await asyncpg.create_pool(database_url())
        yield self.pool
