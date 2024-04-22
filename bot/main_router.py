from aiogram import Dispatcher, types

from .middleware.user_exists_middleware import UserExistsMiddleware


dp = Dispatcher()
dp.message.middleware(UserExistsMiddleware())


@dp.message()
async def echo(message: types.Message):
    await message.answer(message.text)
