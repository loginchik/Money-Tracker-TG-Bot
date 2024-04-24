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
    BotCommand(command='abort', description='Abort current process and erase temp data'),
    BotCommand(command='add_expense_limit', description='Add new expense limit for subcategory'),
    BotCommand(command='delete_my_data', description='Delete all one-related data from database'),
]
# List of commands applied to russian language
commands_ru = [
    BotCommand(command='add_expense', description='Добавить новый расход'),
    BotCommand(command='add_income', description='Добавить новый доход'),
    BotCommand(command='abort', description='Прервать текущий процесс и удалить временные данные'),
    BotCommand(command='add_expense_limit', description='Добавить предел расходов по подкатегории'),
    BotCommand(command='delete_my_data', description='Удалить все связанные с пользователем данные из базы данных'),
]


async def main() -> None:
    """
    Setups bot and starts polling.
    """
    # Set bot commands for all languages and specially for russian
    await bot.delete_my_commands()
    await bot.set_my_commands(commands=commands_en)
    await bot.set_my_commands(commands=commands_ru, language_code='ru')
    # Clear pending updates
    await bot.delete_webhook(drop_pending_updates=True)
    # Start the bot
    await dp.start_polling(bot, debug=True)


if __name__ == '__main__':
    asyncio.run(main())
