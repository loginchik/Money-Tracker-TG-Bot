from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import Command, StateFilter, CommandStart

from bot.static.commands import commands
from bot.middleware.user_language import UserLanguageMiddleware
from bot.static.messages import GENERAL_ROUTER_MESSAGES


general_router = Router()
general_router.message.middleware(UserLanguageMiddleware())


@general_router.message(CommandStart(), StateFilter(None))
async def start_message(message: Message, user_lang: str):
    message_text = GENERAL_ROUTER_MESSAGES['hello'][user_lang]
    await message.answer(message_text)


@general_router.message(Command('help'), StateFilter(None))
async def help_message(message: Message, user_lang: str):
    descr_column = 'ru_long' if user_lang == 'ru' else 'en_long'
    command_descriptions = [
        f'/{command_text}\n{command_descr[descr_column]}' for command_text, command_descr in commands.items()
        if command_text not in ['abort', 'help']
    ]
    commands_text = '\n\n'.join([f'({i + 1}) {text}' for i, text in enumerate(command_descriptions)])

    help_heading = GENERAL_ROUTER_MESSAGES['help_heading'][user_lang]
    help_heading = '<b>' + help_heading + '</b>'
    message_text = '\n\n'.join([help_heading, commands_text])
    await message.answer(message_text, parse_mode=ParseMode.HTML)


@general_router.message(Command('about'), StateFilter(None))
async def about_message(message: Message, user_lang: str):
    message_text = GENERAL_ROUTER_MESSAGES['about'][user_lang]
    await message.answer(message_text)


