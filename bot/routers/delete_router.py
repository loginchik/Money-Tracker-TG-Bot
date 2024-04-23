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
