"""
Entry point for bot application to run.
"""

import asyncio
from aiogram import Bot
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import create_engine
from loguru import logger

from bot.middleware import UserLanguageMiddleware
from bot.routers.delete_router import DeleteRouter
from bot.routers.export_router import ExportRouter
from bot.routers.general_router import GeneralRouter
from bot.routers.new_router import NewRecordRouter
from bot.static.commands import en_commands_list, ru_commands_list
from db.connection import database_url
from db import setup_schemas, insert_or_update_static
from configs import BOT_TOKEN, BOT_ADMIN


async def main_bot_process():
    async def on_startup():
        """
        Send message to admin user on bot startup.
        """
        logger.info('Bot startup')
        await bot.send_message(chat_id=BOT_ADMIN, text='Bot started')

    async def on_shutdown():
        """
        Send message to admin user on bot shutdown.
        """
        logger.info('Bot shutdown')
        await bot.send_message(chat_id=BOT_ADMIN, text='Bot stopped')

    # Create bot object
    defaults = DefaultBotProperties(parse_mode=ParseMode.HTML)
    bot = Bot(token=BOT_TOKEN, default=defaults)
    logger.debug('Created bot instance')

    # Register bot commands
    await bot.set_my_commands(commands=ru_commands_list(), language_code='ru')
    await bot.set_my_commands(commands=en_commands_list())
    logger.debug('Set bot commands')

    # Create engines and sessionmaker to perform database actions in bot
    setup_schemas(test_mode=False, drop_first=False)

    sync_engine = create_engine(database_url(async_=False))
    logger.info('Created sync engine connection with DB')
    async_engine = create_async_engine(database_url(async_=True))
    logger.info('Created async engine connection with DB')
    async_sess_maker = async_sessionmaker(bind=async_engine)
    logger.info('Created async session maker bind to async session')

    await insert_or_update_static(async_sess_maker)

    # Create storage
    storage = MemoryStorage()
    logger.debug(f'Created {storage}')

    # Create dispatcher object and assign database objects as extra parameters to pass to bot
    dispatcher = Dispatcher(async_session=async_sess_maker, sync_engine=sync_engine,
                            storage=storage, events_isolation=SimpleEventIsolation())
    logger.debug(f'Created dispatcher instance: {dispatcher}')

    # Add routers
    delete_router = DeleteRouter()
    export_router = ExportRouter()
    general_router = GeneralRouter()
    new_router = NewRecordRouter()
    dispatcher.include_routers(new_router, export_router, delete_router, general_router)
    logger.debug(f'Added {delete_router.name}, {export_router.name}, {general_router.name}, {new_router.name} to dispatcher')

    # Create user language middleware object assigned to same async_sessionmaker as bot
    user_lang_middleware = UserLanguageMiddleware(async_session_maker=async_sess_maker)
    # Register user language middleware
    dispatcher.message.middleware.register(user_lang_middleware)
    dispatcher.callback_query.middleware.register(user_lang_middleware)
    logger.debug(f'Registered {user_lang_middleware} for messages and callback queries')

    # Register startup and shutdown actions
    dispatcher.startup.register(on_startup)
    dispatcher.shutdown.register(on_shutdown)

    # Clear pending updates
    await bot.delete_webhook(drop_pending_updates=True)
    logger.debug('Deleted pending updates')
    await dispatcher.start_polling(bot, debug=True)


if __name__ == '__main__':
    asyncio.run(main_bot_process())
