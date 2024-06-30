import os

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import Command, StateFilter, CommandStart

from bot.static.commands import commands_dict
from bot.routers import MessageTexts as MT
from configs import BASE_DIR


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
        m_texts = MT('Привет!', 'Hello!')
        return await message.answer(m_texts.get(user_lang))

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
        command_descriptions = []
        for command, command_data in commands_dict.items():
            if command_data[descr_column] is not None:
                command_descr = f'/{command}\n{command_data[descr_column]}'
                command_descriptions.append(command_descr)

        # Collect commands descriptions into numerated list
        commands_text = '\n\n'.join([f'({i + 1}) {text}' for i, text in enumerate(command_descriptions)])
        # Prepend heading for the message
        help_heading = MT(
            ru_text='Доступные команды', en_text='Available commands',
        )
        help_heading = '<b>' + help_heading.get(user_lang) + '</b>'
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
        filename = f'about_{user_lang}.txt'
        filepath = os.path.join(BASE_DIR, 'bot', 'static', filename)

        with open(filepath, 'r', encoding='utf-8') as f:
            about_text = f.read()

        return await message.answer(about_text)
