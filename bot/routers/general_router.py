from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import Command, StateFilter, CommandStart

from bot.static.commands import commands
from bot.static.messages import GENERAL_ROUTER_MESSAGES


class GeneralRouter(Router):
    def __init__(self):
        super().__init__()
        self.name = 'ExportRouter'
        self.register_handlers()

    def register_handlers(self):
        self.message.register(self.start_message, CommandStart(), StateFilter(None))
        self.message.register(self.help_message, Command('help'), StateFilter(None))
        self.message.register(self.about_message, Command('about'), StateFilter(None))

    @staticmethod
    async def start_message(message: Message, user_lang: str):
        """
        Sends start message to user. Automatically triggered
        on user first interaction with the bot.

        Args:
            message (Message): User message.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        message_text = GENERAL_ROUTER_MESSAGES['hello'][user_lang]
        return await message.answer(message_text)

    @staticmethod
    async def help_message(message: Message, user_lang: str):
        """
        Collects all commands besides abort and help long description in user preferred language
        and sends it as numerated list.

        Args:
            message (Message): User message.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
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

    @staticmethod
    async def about_message(message: Message, user_lang: str):
        """
        Sends about message to user.

        Args:
            message (Message): User message.
            user_lang (str): User language.

        Returns:
            Message: Reply message.
        """
        message_text = GENERAL_ROUTER_MESSAGES['about'][user_lang]
        return await message.answer(message_text)
