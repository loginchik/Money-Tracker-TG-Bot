"""
Entry point for bot application to run.
"""

import asyncio
import os.path
import logging

from aiogram import Bot
from aiogram.types import BotCommand
from dotenv import dotenv_values

from bot.routers.main_router import dp
from bot.static.commands import en_commands_list, ru_commands_list


# Start logging
logging.basicConfig(level=logging.INFO)
# Read environment variables to run the bot
secrets_path = os.path.abspath('.env')
secrets = dotenv_values(secrets_path)
# Create bot instance
bot = Bot(token=secrets['BOT_TOKEN'])


async def main() -> None:
    """
    Setups bot and starts polling.
    """
    # Set bot commands for all languages and specially for russian
    deleted = await bot.delete_my_commands()
    if deleted:
        await bot.set_my_commands(commands=en_commands_list())
        await bot.set_my_commands(commands=ru_commands_list(), language_code='ru')
        print(await bot.get_my_commands())
    else:
        print('Did not delete any commands')
    # Clear pending updates
    await bot.delete_webhook(drop_pending_updates=True)
    # Start the bot
    await dp.start_polling(bot, debug=True)


if __name__ == '__main__':
    asyncio.run(main())
