import os.path

from loguru import logger
from dotenv import dotenv_values

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SECRETS_PATH = os.path.join(BASE_DIR, '.env')

secrets = dotenv_values(SECRETS_PATH)
DEBUG = True
DB_HOST = secrets['DB_HOST']
DB_PORT = secrets['DB_PORT']
DB_USER_NAME = secrets['DB_USER_NAME']
DB_PASSWORD = secrets['DB_PASSWORD']
DB_URL_DEV = secrets['DB_URL_DEV_BASE']
DB_URL_PROD = secrets['DB_URL_PROD_BASE']

if DEBUG:
    DB_NAME = secrets['DB_NAME_DEV']
else:
    DB_NAME = secrets['DB_NAME_PROD']

TEST_DB_NAME = secrets['DB_NAME_TEST']

BOT_TOKEN = secrets['BOT_TOKEN']
BOT_ADMIN = secrets['BOT_ADMIN']

WEBHOOK_PATH = secrets['WEBHOOK_PATH']
WEBHOOK_URL = f"{secrets['WEBHOOK_HOST']}{WEBHOOK_PATH}"
WEBAPP_HOST = secrets['WEBAPP_HOST']
WEBAPP_PORT = secrets['WEBAPP_PORT']

if DEBUG:
    sync_engine = create_engine(url=f'postgresql://{DB_URL_DEV}')
else:
    sync_engine = create_engine(url=f'postgresql://{DB_URL_PROD}')
logger.info('Created sync engine connection with DB')

if DEBUG:
    async_engine = create_async_engine(url=f'postgresql+asyncpg://{DB_URL_DEV}')
else:
    async_engine = create_async_engine(url=f'postgresql+asyncpg://{DB_URL_PROD}')
logger.info('Created async engine connection with DB')


async_sess_maker = async_sessionmaker(bind=async_engine)
logger.info('Created async session maker bind to async session')


scheduler = AsyncIOScheduler(
    timezone='Europe/Moscow',
    jobstores={
        'default': SQLAlchemyJobStore(engine=sync_engine, tablename='scheduled_jobs', tableschema='user_based')
    }
)
logger.info('Created scheduler instance')