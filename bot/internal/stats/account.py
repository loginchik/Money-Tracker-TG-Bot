import datetime as dt

import asyncpg

from bot.static.messages import STATS_ROUTER_MESSAGES


async def get_account_stats(user_id: int, user_lang: str, db_connection: asyncpg.Connection) -> str:
    """
    Gets user registration date, total expenses count, total expenses sum,
    total incomes count, total incomes sum. Generates report text according to pattern.
    :param user_id: User telegram id.
    :param user_lang: User language.
    :param db_connection: Database connection.
    :return: Report text.
    """
    user_registration = await db_connection.fetchval('''SELECT u.registration_date FROM 
    shared.user u WHERE u.tg_id = $1;''', user_id)
    expenses_stat = await db_connection.fetchrow(f'''SELECT count(*), sum(amount) FROM 
    user_based.expense_{user_id};''')
    incomes_stat = await db_connection.fetchrow(f'''SELECT count(*), sum(amount) FROM 
    user_based.income_{user_id};''')

    registration_date_str = dt.datetime.strftime(user_registration, '%d.%m.%Y')
    registration_lambda_days = (dt.date.today() - user_registration).days + 1

    expenses_sum = expenses_stat['sum']
    incomes_sum = incomes_stat['sum']
    expenses_sum = int(expenses_sum) if expenses_sum % 1 == 0 else float(expenses_sum)
    incomes_sum = int(incomes_sum) if incomes_sum % 1 == 0 else float(incomes_sum)

    report_text = STATS_ROUTER_MESSAGES['account_stats'][user_lang]
    report_text_formatted = report_text.format(registration_lambda_days, registration_date_str,
                                               int(expenses_stat['count']), expenses_sum,
                                               int(incomes_stat['count']),incomes_sum,
    )
    return report_text_formatted
