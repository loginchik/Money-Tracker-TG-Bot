import asyncio

from db.connection import DBPoolGenerator

pool_generator = DBPoolGenerator()


async def delete_old_limits():
    async for pool in pool_generator():
        async with pool.acquire() as connection:
            async with connection.transaction():
                query = '''DELETE FROM user_based.expense_limit el WHERE el.end_date::date < now()::date;'''
                await connection.execute(query)
                print('Deleted old limits')


async def update_outdated_limits():
    async for pool in pool_generator():
        async with pool.acquire() as connection:
            query = '''SELECT count(*) FROM user_based.expense_limit el 
            WHERE el.current_period_end::date < now()::date;'''
            count = await connection.fetchval(query)
            print('Outdated:', count)

            query = '''UPDATE user_based.expense_limit el
            set current_period_start = date_add(current_period_end, '1 day'::interval)::date, 
            current_balance = (case when cumulative = 'true' then current_balance + limit_value else limit_value end)
            where el.current_period_end::date < now()::date;'''
            await connection.execute(query)
            print('Updated outdated limits')


if __name__ == '__main__':
    current_loop = asyncio.get_event_loop()
    current_loop.run_until_complete(delete_old_limits())
    current_loop.run_until_complete(update_outdated_limits())
