from aiogram import Dispatcher
from .new_router import new_record_router

dp = Dispatcher()
dp.include_router(new_record_router)

