"""
Filter that checks if a user exists.
"""
from aiogram.filters import BaseFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

from db.connection import database_url
from db.shared_schema import BotUser


engine = create_async_engine(database_url(async_=True))
session_maker = async_sessionmaker(bind=engine)


class UserExists(BaseFilter):
    """
    Checks if user is present in users table in DB.
    """
    def __init__(self):
        super().__init__()

    async def __call__(self, message: Message) -> bool:
        user_id = message.from_user.id
        status = await BotUser.exists(user_id=user_id, async_session=session_maker)
        return status is True
