"""
Package contains scripts that create connection to the database. Main function for export and
external use is ``create_connection``.
"""
import logging
import os

import asyncpg
import psycopg2
from settings import db_secrets


def database_url() -> str:
    """
    Get database URL from environment variables.
    :return: DB URL.
    """
    user_password = f'{db_secrets["DB_USER"]}:{db_secrets["DB_PASSWORD"]}'
    host_port_dbname = f'{db_secrets["DB_HOST"]}:{db_secrets["DB_PORT"]}/{db_secrets["DB_NAME"]}'
    db_url = f'postgresql://{user_password}@{host_port_dbname}'
    return db_url


async def create_connection() -> asyncpg.Connection | None:
    """
    Creates database async connection.
    :return: Async connection to DB.
    """

    db_url = database_url()
    try:
        connection = await asyncpg.connect(dsn=db_url)
        return connection
    except Exception as e:
        logging.critical(e)
        return None


def create_sync_connection():
    """
    Creates database sync connection.
    :return: Sync connection to DB via psycopg2.
    """
    db_url = database_url()
    try:
        connection = psycopg2.connect(dsm=db_url)
        return connection
    except Exception as e:
        logging.critical(e)
        return None
