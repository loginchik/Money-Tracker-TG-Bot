from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware, Bot
from aiogram.types import Message, TelegramObject

from db import connection, user_status


class UserExistsMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()

    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
                       event: Message, data: Dict[str, Any]):
        # Get user id from message data
        user_id = event.from_user.id
        # Check if user exists in database
        database_connection = await connection.create_connection()
        exists_status = await user_status.user_exists(user_id, database_connection)
        # Difference scenarios for both situations
        if exists_status:
            print(f'User {user_id} exists in db')
        else:
            print(f'User {user_id} does not exist, we need to create one')
        # Handle message
        result = await handler(event, data)
        # Close DB connection
        await database_connection.close()
        return result

