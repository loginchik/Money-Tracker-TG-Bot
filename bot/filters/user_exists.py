"""
Filter that checks if a user exists.
"""

from aiogram.filters import BaseFilter
from aiogram.types import Message

from db.connection import create_connection
from db.user_operations import user_exists


class UserExists(BaseFilter):
    """
    Checks if user is present in users table in DB.
    """
    def __init__(self):
        super().__init__()

    async def __call__(self, message: Message) -> bool:
        # Create async connection to DB
        db_connection = await create_connection()
        # Get user status
        user_id = message.from_user.id
        status: bool = await user_exists(user_id, db_connection)
        # Close connection to DB
        await db_connection.close()
        # Return user status
        return status
