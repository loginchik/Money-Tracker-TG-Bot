from aiogram import BaseMiddleware
from aiogram.types import Message

from db.shared_schema import BotUser
from bot.static.user_languages import USER_LANGUAGE_PREFERENCES


class UserLanguageMiddleware(BaseMiddleware):
    """
    Adds user_lang argument to handler to perform user-specific actions in bot.
    """
    def __init__(self):
        super().__init__()

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
            user = await BotUser.get_by_id(user_id=user_id)
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
