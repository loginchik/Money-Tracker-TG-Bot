"""
Filter that checks if a user exists.
"""
import logging

import asyncpg
from aiogram.filters import BaseFilter
from aiogram.types import Message

from db.connection import database_url
from db.user_operations import user_exists


class DBPoolGenerator:
    def __init__(self):
        self.pool = None

    async def __call__(self):
        if self.pool is None:
            self.pool = await asyncpg.create_pool(database_url())
            logging.info('Created pool')

        yield self.pool


pool_generator = DBPoolGenerator()


class UserExists(BaseFilter):
    """
    Checks if user is present in users table in DB.
    """
    def __init__(self):
        super().__init__()

    async def __call__(self, message: Message) -> bool:
        async for pool in pool_generator():
            async with pool.acquire() as connection:
                # Get user status
                user_id = message.from_user.id
                status: bool = await user_exists(user_id, connection)
            # Return user status
            return status
