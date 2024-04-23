"""
Package contains scripts to address delete queries to db. Supports user data deletion process.
Runs on its own router - ``delete_router`` which must be included into main router or any other router
that is included into main to be able to get and handle pending updates.
"""


from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import db.user_operations


delete_router = Router()


@delete_router.message(Command(commands=['delete_my_data']))
async def delete_user_data(message: Message):
    user_id = message.from_user.id
    try:
        await db.user_operations.delete_user_data(user_id)
        await message.answer('All data deleted.')
    except Exception as e:
        print(e)
        await message.answer('Sorry, try again later')
