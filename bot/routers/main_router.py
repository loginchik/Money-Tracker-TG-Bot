"""
Package contains dispatcher, or main router. All the routers are connected to each other in the package.
"""


from aiogram import Dispatcher

from bot.routers.new_router import new_record_router
from bot.routers.delete_router import delete_router
from bot.routers.general_router import general_router
from bot.routers.export_router import export_router


dp = Dispatcher()
dp.include_router(general_router)
dp.include_router(new_record_router)
dp.include_router(delete_router)
dp.include_router(export_router)
