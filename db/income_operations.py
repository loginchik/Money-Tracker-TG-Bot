import datetime as dt

from db.connection import create_connection


async def add_income(user_id: int, amount: float | int, passive: bool, event_date: dt.date):
    connection = await create_connection()
    query = '''INSERT INTO user_based.income (user_id, amount, passive, event_date) VALUES ($1, $2, $3, $4);'''
    await connection.execute(query, user_id, amount, passive, event_date)
    await connection.close()
