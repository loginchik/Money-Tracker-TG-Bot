import datetime
from decimal import Decimal

from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest


class CommonRouter:
    @staticmethod
    async def clear_inline_markup(source, bot):
        """
        Removes inline markup from bot message, if possible.

        Args:
             source (Message | CallbackQuery): Message or callback query to define inline markup source.
             bot (Bot): Bot instance.
        """
        if isinstance(source, CallbackQuery):
            return await bot.edit_message_reply_markup(chat_id=source.message.chat.id,
                                                       message_id=source.message.message_id,
                                                       reply_markup=None)
        elif isinstance(source, Message):
            try:
                await bot.edit_message_reply_markup(chat_id=source.chat.id, message_id=source.message_id - 1,
                                                    reply_markup=None)
            except TelegramBadRequest:
                pass


class MessageTexts:
    def __init__(self, ru_text, en_text):
        """
        Creates instance.

        Args:
            ru_text (str): Text to be sent to russian-speaking users.
            en_text (str): Text to be sent to english-speaking users.
        """
        self.ru = ru_text
        self.en = en_text

    def get(self, user_lang):
        if user_lang == 'ru':
            return self.ru
        else:
            return self.en

    @staticmethod
    def format_float(value):
        """
        Formats float value.

        Args:
            value (float): Value to be formatted.

        Returns:
            str: Formatted value.
        """
        if isinstance(value, float) or isinstance(value, Decimal):
            return f'{value:.2f}'
        else:
            return float

    @staticmethod
    def format_date(value):
        """
        Formats date or datetime value.

        Args:
            value (datetime.datetime | datetime.date): Value to be formatted.

        Returns:
            str: Formatted value.
        """
        if isinstance(value, datetime.datetime):
            return value.strftime('%d.%m.%Y %H:%M')
        if isinstance(value, datetime.date):
            return value.strftime('%d.%m.%Y')
