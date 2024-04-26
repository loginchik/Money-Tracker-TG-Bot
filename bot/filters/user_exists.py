"""
Filter that checks if a user exists.
"""

from aiogram.filters import BaseFilter
from aiogram.types import Message

from db.connection import DBPoolGenerator
from db.user_operations import user_exists


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
