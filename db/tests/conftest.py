import asyncio
import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from db import setup_schemas
from db.connection import database_url


@pytest_asyncio.fixture(scope="class")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class TestDBBase:

    @classmethod
    def setup_class(cls):
        setup_schemas(test_mode=True, drop_first=True)
        db_url = database_url(async_=True, test=True)
        cls.engine = create_async_engine(db_url)
        cls.maker = async_sessionmaker(cls.engine, class_=AsyncSession, expire_on_commit=False)

    @classmethod
    def teardown_class(cls):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(cls.engine.dispose())