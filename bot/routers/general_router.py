from aiogram import Router, Bot
from aiogram.enums import ParseMode
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types.web_app_info import WebAppInfo
from aiogram.filters import Command, StateFilter, CommandStart

from bot.static.commands import commands
from bot.middleware.user_language import UserLanguageMiddleware
from bot.static.messages import GENERAL_ROUTER_MESSAGES


general_router = Router()
general_router.message.middleware(UserLanguageMiddleware())


@general_router.message(CommandStart(), StateFilter(None))
async def start_message(message: Message, user_lang: str):
    """
    Sends start message to user. Automatically triggered
    on user first interaction with the bot.
    :param message: User message.
    :param user_lang: User language.
    :return: Message.
    """
    message_text = GENERAL_ROUTER_MESSAGES['hello'][user_lang]
    return await message.answer(message_text)


@general_router.message(Command('help'), StateFilter(None))
async def help_message(message: Message, user_lang: str):
    """
    Collects all commands besides abort and help long description in user preferred language
    and sends it as numerated list.
    :param message: User message.
    :param user_lang: User language.
    :return: Message.
    """
    # Define description column based on user language
    descr_column = 'ru_long' if user_lang == 'ru' else 'en_long'
    # Collect list of commands descriptions
    command_descriptions = [
        f'/{command_text}\n{command_descr[descr_column]}' for command_text, command_descr in commands.items()
        if command_text not in ['abort', 'help']
    ]
    # Collect commands descriptions into numerated list
    commands_text = '\n\n'.join([f'({i + 1}) {text}' for i, text in enumerate(command_descriptions)])
    # Prepend heading for the message
    help_heading = GENERAL_ROUTER_MESSAGES['help_heading'][user_lang]
    help_heading = '<b>' + help_heading + '</b>'
    message_text = '\n\n'.join([help_heading, commands_text])
    # Send help info to user
    return await message.answer(message_text, parse_mode=ParseMode.HTML)


@general_router.message(Command('about'), StateFilter(None))
async def about_message(message: Message, user_lang: str):
    """
    Sends about message to user.
    :param message: User message.
    :param user_lang: User language.
    :return: Message.
    """
    message_text = GENERAL_ROUTER_MESSAGES['about'][user_lang]
    return await message.answer(message_text)


@general_router.message(Command('app'), StateFilter(None))
async def app_open(message: Message, user_lang: str, bot: Bot):
    button_text = 'Открыть приложение' if user_lang == 'ru' else 'Launch the app'
    webapp = WebAppInfo(url='https://google.com')
    open_app_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=button_text, web_app=webapp)]
        ]
    )
    await bot.send_dice(chat_id=message.chat.id)
    message_text = GENERAL_ROUTER_MESSAGES['launch_app'][user_lang]
    await message.answer(message_text, reply_markup=open_app_keyboard)
