from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message

from db.connection import create_connection
from bot.static.user_languages import USER_LANGUAGE_PREFERENCES


class UserLanguageMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()

    async def __call__(self, handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
                       event: Message, data: Dict[str, Any]):

        user_id = event.from_user.id
        # User has not interacted with the bot since its start
        if user_id not in list(USER_LANGUAGE_PREFERENCES.keys()):
            # Connect to db
            db_conn = await create_connection()
            # Get user preferred language from db data
            query = '''SELECT lang from shared.user where tg_id = $1;'''
            result = await db_conn.fetchval(query, user_id)
            # Close connection to db
            await db_conn.close()

            # If result is not empty, save it to local dictionary not to connect to db the next time
            # and append user language to handler data
            if result is not None:
                USER_LANGUAGE_PREFERENCES[user_id] = result
                data['user_lang'] = USER_LANGUAGE_PREFERENCES[user_id]
            else:
                # Otherwise, set language to telegram language
                user_tg_language = event.from_user.language_code
                data['user_lang'] = user_tg_language if user_tg_language in ['en', 'ru'] else 'en'
        # If user is present in local dictionary, it's mush easier
        else:
            data['user_lang'] = USER_LANGUAGE_PREFERENCES[user_id]
        # Handle the event
        return await handler(event, data)
