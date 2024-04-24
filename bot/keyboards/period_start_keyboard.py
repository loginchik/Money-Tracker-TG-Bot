import datetime as dt

from aiogram.utils.keyboard import InlineKeyboardMarkup, InlineKeyboardButton, InlineKeyboardBuilder


async def generate_period_start_keyboard(user_period: int):
    current_date = dt.date.today()

    if user_period == 1:
        current_dayofweek = current_date.weekday()
        next_monday_lambda = 7 - current_dayofweek
        prev_monday = (current_date - dt.timedelta(days=current_dayofweek)).strftime('%d.%m.%Y')
        next_monday = (current_date + dt.timedelta(days=next_monday_lambda)).strftime('%d.%m.%Y')
        first_button = InlineKeyboardButton(text=prev_monday, callback_data=prev_monday)
        second_button = InlineKeyboardButton(text=next_monday, callback_data=next_monday)

    elif user_period == 3:
        this_year_start = dt.date(current_date.year, 1, 1).strftime('%d.%m.%Y')
        next_year_start = dt.date(current_date.year + 1, 1, 1).strftime('%d.%m.%Y')
        first_button = InlineKeyboardButton(text=this_year_start, callback_data=this_year_start)
        second_button = InlineKeyboardButton(text=next_year_start, callback_data=next_year_start)

    else:
        this_month_start = dt.date(current_date.year, current_date.month, 1).strftime('%d.%m.%Y')
        next_month = current_date.month + 1 if current_date.month != 12 else 1
        next_year = current_date.year if next_month > 1 else current_date.year + 1
        next_month_start = dt.date(next_year, next_month, 1).strftime('%d.%m.%Y')
        first_button = InlineKeyboardButton(text=this_month_start, callback_data=this_month_start)
        second_button = InlineKeyboardButton(text=next_month_start, callback_data=next_month_start)

    keyboard = InlineKeyboardBuilder()
    keyboard.add(first_button, second_button)
    return keyboard.as_markup()
