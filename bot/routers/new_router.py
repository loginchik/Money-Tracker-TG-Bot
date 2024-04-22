from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from bot.filters.user_exists import UserExists


# Router to handle new records creation process
new_record_router = Router()


# Check if user is registered
@new_record_router.message(Command(commands='add_expense'), ~UserExists())
@new_record_router.message(Command(commands='add_income'), ~UserExists())
async def add_expense(message: Message):
    await message.answer('You are not registered yet')


@new_record_router.message(Command(commands=['add_expense']), UserExists())
async def add_expense_init(message: Message):
    await message.answer('New expense creation started')


@new_record_router.message(Command(commands=['add_income']), UserExists())
async def add_income_init(message: Message):
    await message.answer('New income creation started')

