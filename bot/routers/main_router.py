from aiogram import Dispatcher

from bot.routers.new_router import new_record_router
from bot.routers.delete_router import delete_router


dp = Dispatcher()
dp.include_router(new_record_router)
dp.include_router(delete_router)
