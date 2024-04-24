from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, StateFilter, CommandStart

from bot.static.commands import commands
from bot.middleware.user_language import UserLanguageMiddleware


general_router = Router()
general_router.message.middleware(UserLanguageMiddleware())


@general_router.message(CommandStart(), StateFilter(None))
async def start_message(message: Message, user_lang: str):
    await message.answer('Hello!')


@general_router.message(Command('help'), StateFilter(None))
async def help_message(message: Message, user_lang: str):
    await message.answer('Help!')


@general_router.message(Command('about'), StateFilter(None))
async def about_message(message: Message):
    await message.answer('About!')


