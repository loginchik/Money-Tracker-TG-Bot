"""
Filter that checks if a user exists.
"""
from aiogram.filters import BaseFilter
from aiogram.types import Message

from db.shared_schema import BotUser


class UserExists(BaseFilter):
    """
    Checks if user is present in users table in DB.
    """
    def __init__(self):
        super().__init__()

    async def __call__(self, message: Message) -> bool:
        user_id = message.from_user.id
        status = await BotUser.exists(user_id=user_id)
        return status is True
