"""
Entry point for bot application to run.
"""

import asyncio
import logging

from aiogram import Bot
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.routers.main_router import dp
from bot.static.commands import en_commands_list, ru_commands_list
from settings import bot_secrets


# Start logging
logging.basicConfig(level=logging.INFO)
# Create bot instance
props = DefaultBotProperties(parse_mode=ParseMode.HTML)
bot = Bot(token=bot_secrets['BOT_TOKEN'], default=props)


async def on_startup():
    await bot.send_message(chat_id=bot_secrets['ADMIN'], text='Bot started')


async def on_shutdown():
    await bot.send_message(chat_id=bot_secrets['ADMIN'], text='Bot stopped')


dp.startup.register(on_startup)
dp.shutdown.register(on_shutdown)


async def main() -> None:
    """
    Setups bot and starts polling.
    """
    # Set bot commands for all languages and specially for russian
    await bot.set_my_commands(commands=ru_commands_list(), language_code='ru')
    await bot.set_my_commands(commands=en_commands_list())
    # Clear pending updates
    await bot.delete_webhook(drop_pending_updates=True)
    # Start the bot
    await dp.start_polling(bot, debug=True)


if __name__ == '__main__':
    asyncio.run(main())
