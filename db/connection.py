"""
Package contains scripts that create connection to the database. Main function for export and
external use is ``create_connection``.
"""

import asyncpg
from configs import DB_HOST, DB_PORT, DB_NAME, DB_USER_NAME, DB_PASSWORD, TEST_DB_NAME


def database_url(async_=False, test=False) -> str:
    """
    Get database URL from environment variables.

    Args:
        async_ (bool): Asynchronous mode.
        test (bool): Test database connection.

    Returns:
        str: Database URL.
    """
    user_password = f'{DB_USER_NAME}:{DB_PASSWORD}'
    host_port_dbname = f'{DB_HOST}:{DB_PORT}/{TEST_DB_NAME if test else DB_NAME}'
    if not async_:
        return f'postgresql://{user_password}@{host_port_dbname}'
    else:
        return f'postgresql+asyncpg://{user_password}@{host_port_dbname}'


class DBPoolGenerator:
    def __init__(self):
        self.pool = None

    async def __call__(self):
        if self.pool is None:
            self.pool = await asyncpg.create_pool(database_url())
        yield self.pool
