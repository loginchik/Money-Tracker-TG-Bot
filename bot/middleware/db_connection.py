import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
import asyncpg

from db.connection import database_url


class DBConnectionMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.pool = None

    async def __call__(self, handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
                       event: Message | CallbackQuery, data: Dict[str, Any]):

        if self.pool is None:
            self.pool = await asyncpg.create_pool(dsn=database_url())

        async with self.pool.acquire() as connection:
            data['db_con'] = connection
            await handler(event, data)

        return
