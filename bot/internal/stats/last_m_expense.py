import datetime as dt
import logging
from io import BytesIO

import asyncpg
import matplotlib.pyplot as plt

from db.expense_operations import get_user_expenses_in_daterange


BG_COLOR = '#F3F8FF'
BAR_COLOR = '#7E30E1'


def categories_bar(stats, user_lang: str) -> bytes:
    plt.rcParams['font.family'] = 'Helvetica Neue, sans serif'

    figure_height = max(2, round(stats.shape[0] * 0.5))
    figure, axes = plt.subplots(nrows=1, ncols=1, dpi=144, figsize=(10, figure_height), facecolor=BG_COLOR)
    axes.set_facecolor(BG_COLOR)

    axes.barh(y=stats.index, width=stats.values, color=BAR_COLOR)
    xlabel_text = 'Сумма' if user_lang == 'ru' else 'Sum'
    axes.set_xlabel(xlabel_text, color=BAR_COLOR)
    axes.set_title(dt.datetime.now().strftime('%d.%m.%Y'), color=BAR_COLOR)
    # Configure spices: hide top and left, color bottom and right
    axes.spines['top'].set_visible(False)
    axes.spines['right'].set_visible(False)
    axes.spines['left'].set_color(BAR_COLOR)
    axes.spines['bottom'].set_color(BAR_COLOR)
    # Configure ticks colors
    axes.tick_params(axis='x', colors=BAR_COLOR)
    axes.tick_params(axis='y', colors=BAR_COLOR)
    max_value = stats.values.max()
    for i, val in enumerate(stats.values):
        axes.text(x=val + 0.01 * max_value, y=i - 0.1, s=str(val), color=BAR_COLOR)

    plt.tight_layout()

    # Save to bytes
    buffer = BytesIO()
    try:
        figure.savefig(buffer, format='png')
        buffer.seek(0)
        buffer.getvalue()
        return buffer.getvalue()
    except Exception as e:
        logging.error(e)
    finally:
        buffer.close()


def dates_linechart(stats):
    plt.rcParams['font.family'] = 'Helvetica Neue, sans serif'
    figure, axes = plt.subplots(nrows=1, ncols=1, dpi=144, figsize=(10, 5), facecolor=BG_COLOR)
    axes.set_facecolor(BG_COLOR)

    axes.plot(stats.index, stats.values, color=BAR_COLOR)
    axes.set_title(dt.datetime.now().strftime('%d.%m.%Y'), color=BAR_COLOR)
    axes.spines['top'].set_visible(False)
    axes.spines['right'].set_visible(False)
    axes.spines['left'].set_color(BAR_COLOR)
    axes.spines['bottom'].set_color(BAR_COLOR)
    axes.tick_params(axis='x', colors=BAR_COLOR)
    axes.tick_params(axis='y', colors=BAR_COLOR)

    axes.set_xticks(list(stats.index), list(stats.index))
    plt.tight_layout()

    # Save to bytes
    buffer = BytesIO()
    try:
        figure.savefig(buffer, format='png')
        buffer.seek(0)
        buffer.getvalue()
        return buffer.getvalue()
    except Exception as e:
        logging.error(e)
    finally:
        buffer.close()


async def get_last_month_expenses(user_id: int, user_lang: str, db_connection: asyncpg.Connection):
    end_date = dt.date.today()
    start_date = end_date - dt.timedelta(days=30)
    data = await get_user_expenses_in_daterange(user_id, user_lang, db_connection, start_date, end_date)
    if data.shape[0] == 0:
        return None

    categories_stat = data.groupby('expense_category')['amount'].sum().sort_values(ascending=True)
    categories_bar_bytes = categories_bar(categories_stat, user_lang)

    subcategories_stat = data.groupby('expense_subcategory')['amount'].sum().sort_values(ascending=True)
    subcategories_bar_bytes = categories_bar(subcategories_stat, user_lang)

    day_stat = data.groupby(data['event_time'].dt.date)['amount'].sum().sort_index(ascending=True)
    day_stat_bar = dates_linechart(day_stat)
    return categories_bar_bytes, subcategories_bar_bytes, day_stat_bar
