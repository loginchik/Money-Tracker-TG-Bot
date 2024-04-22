import asyncio
import os.path
import logging

from aiogram import Bot
from aiogram.types import BotCommand
from dotenv import dotenv_values

from bot.main_router import dp


# Start logging
logging.basicConfig(level=logging.INFO)
# Read environment variables to run the bot
secrets_path = os.path.abspath('.env')
secrets = dotenv_values(secrets_path)
# Create bot instance
bot = Bot(token=secrets['BOT_TOKEN'])
# List of commands applied to all languages
commands_en = [
    BotCommand(command='add_expense', description='Add new expense'),
    BotCommand(command='add_income', description='Add new income'),
]
# List of commands applied to russian language
commands_ru = [
    BotCommand(command='add_expense', description='Добавить новый расход'),
    BotCommand(command='add_income', description='Добавить новый доход'),
]


async def main() -> None:
    """
    Setups bot and starts polling.
    """
    # Set bot commands for all languages and specially for russian
    await bot.set_my_commands(commands=commands_en)
    await bot.set_my_commands(commands=commands_ru, language_code='ru')
    # Clear pending updates
    await bot.delete_webhook(drop_pending_updates=True)
    # Start the bot
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
