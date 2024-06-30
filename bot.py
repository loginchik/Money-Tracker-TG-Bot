"""
Entry point for bot application to run.
"""

import asyncio
import os

from aiohttp import web
from aiogram import Bot
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from loguru import logger

from bot.middleware import UserLanguageMiddleware
from bot.routers import DeleteRouter, ExportRouter, GeneralRouter, NewRecordRouter, StatsRouter
from bot.static.commands import en_commands_list, ru_commands_list
from db import insert_or_update_static

from configs import (BOT_TOKEN, BOT_ADMIN,
                     scheduler, sync_engine, async_sess_maker,
                     WEBAPP_HOST, WEBAPP_PORT, WEBHOOK_URL,
                     DEBUG)


os.makedirs('logs', exist_ok=True)
logger.configure(handlers=[
    {
        'sink': 'logs/{time:%Y%m%d}.log',
        'level': 'DEBUG',
        'rotation': '00:00'
    }
])


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

    await insert_or_update_static()

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
    stats_router = StatsRouter()
    routers = [new_router, export_router, delete_router, stats_router, general_router]
    dispatcher.include_routers(*routers)
    logger.debug(f'Added {", ".join([r.name for r in routers])} to dispatcher')

    # Create user language middleware object assigned to same async_sessionmaker as bot
    user_lang_middleware = UserLanguageMiddleware()
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
    scheduler.start()

    if DEBUG:
        await dispatcher.start_polling(bot, debug=DEBUG)
    else:
        app = web.Application()
        webhook_requests_handler = SimpleRequestHandler(dispatcher=dispatcher, bot=bot, handle_in_background=False)
        webhook_requests_handler.register(app=app, path=WEBHOOK_URL)
        setup_application(app=app, dispatcher=dispatcher, bot=bot)
        web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)


if __name__ == '__main__':
    asyncio.run(main_bot_process())
