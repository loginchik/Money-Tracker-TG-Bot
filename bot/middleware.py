# from sqlalchemy import create_engine
# from sqlalchemy.ext.asyncio import create_async_engine
# from sqlalchemy.ext.asyncio import async_sessionmaker
from aiogram import BaseMiddleware
from aiogram.types import Message

# from db.connection import database_url
from db.shared_schema import BotUser
from bot.static.user_languages import USER_LANGUAGE_PREFERENCES
#
# class AsyncSessionMiddleware(BaseMiddleware):
#     """
#     Adds async_session argument with async_sessionmaker assigned into event data dictionary.
#     Thus, it is possible to query data from database in async mode and perform some asynchronous
#     actions in db from bot.
#     """
#     def __init__(self):
#         super().__init__()
#
#     async def __call__(self, handler, event, data):
#         """
#         Add async_sessionmaker to handler data and perform bot action.
#
#         Args:
#             handler (Callable[[Message, Dict[str, Any]], Awaitable[Any]]): Handler to perform bot action.
#             event (Message | CallbackQuery): Event type. Doesn't matter for middleware performance.
#             data (Dict[str, Any]): Handler data to perform action.
#         """
#         data['async_session'] = async_sess_maker
#         await handler(event, data)
#
#
# class SyncEngineMiddleware(BaseMiddleware):
#     """
#     Adds sync_engine argument with synchronous sqlalchemy.engine.Engine object to perform pandas
#     and geopandas operations during bot event handling.
#     """
#     def __init__(self):
#         super().__init__()
#
#     async def __call__(self, handler, event, data):
#         """
#         Add async_sessionmaker to handler data and perform bot action.
#
#         Args:
#             handler (Callable[[Message, Dict[str, Any]], Awaitable[Any]]): Handler to perform bot action.
#             event (Message | CallbackQuery): Event type. Doesn't matter for middleware performance.
#             data (Dict[str, Any]): Handler data to perform action.
#         """
#         global sync_engine
#
#         data['sync_engine'] = sync_engine
#         await handler(event, data)


class UserLanguageMiddleware(BaseMiddleware):
    """
    Adds user_lang argument to handler to perform user-specific actions in bot.
    """
    def __init__(self, async_session_maker):
        super().__init__()
        self.sess_maker = async_session_maker

    async def __call__(self, handler, event, data):
        """
        Add user_lang to handler data and perform bot action.

        Args:
            handler (Callable[[Message, Dict[str, Any]], Awaitable[Any]]): Handler to perform bot action.
            event (Message): Event type. Doesn't matter for middleware performance.
            data (Dict[str, Any]): Handler data to perform action.
        """
        # Get user id
        user_id = event.from_user.id

        # User has not interacted with the bot since its start
        if user_id not in list(USER_LANGUAGE_PREFERENCES.keys()):
            # Get user object from DB to query language preference
            user = await BotUser.get_by_id(user_id=user_id, async_session=self.sess_maker)
            if user is not None:
                USER_LANGUAGE_PREFERENCES[user_id] = user.__getattribute__('lang')
                data['user_lang'] = user.__getattribute__('lang')
            else:
                # If user is not present in DB, set language to telegram language
                user_tg_language = event.from_user.language_code
                data['user_lang'] = user_tg_language if user_tg_language in ['en', 'ru'] else 'en'
        # If user is present in local dictionary, it's mush easier
        else:
            data['user_lang'] = USER_LANGUAGE_PREFERENCES[user_id]

        await handler(event, data)
