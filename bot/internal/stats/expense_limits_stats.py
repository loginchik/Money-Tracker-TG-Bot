import datetime as dt
import logging
from io import BytesIO

import asyncpg
import pandas as pd
import matplotlib.pyplot as plt

from db.expense_limit_operations import user_expense_limits_info


BG_COLOR = '#F3F8FF'
BAR_COLOR = '#7E30E1'


def limits_bar(stats: pd.DataFrame, user_lang: str) -> bytes:
    plt.rcParams['font.family'] = 'Helvetica Neue, sans serif'

    stats = stats.sort_values(by=['free'], ascending=True)
    # Create figure and axes. Figure size depends on expense limits count to adjust graph height
    figure_height = max(2, round(stats.shape[0] * 0.5))
    figure, axes = plt.subplots(nrows=1, ncols=1, dpi=144, figsize=(10, figure_height), facecolor=BG_COLOR)
    axes.set_facecolor(BG_COLOR)

    # Put bars on graph
    axes.barh(width=stats['free'], y=stats['title'], color=BAR_COLOR, height=0.6)
    # Put line on 0
    axes.axvline(x=0, color=BAR_COLOR, lw=0.75)
    # Put limits headers on graph
    for i in range(stats.shape[0]):
        axes.text(x=stats['free'][i] + 1 if stats['free'][0] > 0 else 1,
                  y=i - 0.1,
                  s=stats['title'][i],
                  color=BAR_COLOR
                  )

    # Set ticks
    axes.set_xticks(range(-100, 101, 25), range(-100, 101, 25))
    axes.set_yticks([], [])
    xlabel_text = 'Доступный баланс, % от предела' if user_lang == 'ru' else 'Balance available, % of limit'
    axes.set_xlabel(xlabel_text, color=BAR_COLOR)
    axes.set_title(dt.datetime.now().strftime('%d.%m.%Y'), color=BAR_COLOR)
    # Configure spices: hide top and left, color bottom and right
    axes.spines['top'].set_visible(False)
    axes.spines['left'].set_visible(False)
    axes.spines['left'].set_color(BAR_COLOR)
    axes.spines['bottom'].set_color(BAR_COLOR)
    axes.spines['right'].set_visible(False)
    # Configure ticks colors
    axes.tick_params(axis='x', colors=BAR_COLOR)
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


async def expense_limits_stats(user_id: int, db_connection: asyncpg.Connection, user_lang: str) -> [str, bytes]:
    pd.options.display.float_format = '{:,.2f}'.format
    stats = await user_expense_limits_info(user_id, db_connection, user_lang)
    if stats.shape[0] == 0:
        return None
    stats['free'] = (stats['balance'] / stats['limit']) * 100
    stats['balance'] = stats['balance'].astype(float)
    stats['limit'] = stats['limit'].astype(float)
    graph = limits_bar(stats, user_lang)

    descriptions = []
    for i in range(stats.shape[0]):
        category_subcategory = ' / '.join([stats['category'][i], stats['subcategory'][i]])
        current_period_label = 'Текущий период' if user_lang == 'ru' else 'Current period'

        period_range = '-'.join([stats['period_start'][i].strftime('%d.%m.%Y'),
                                 stats['period_end'][i].strftime('%d.%m.%Y')])
        balance_label = 'Доступный баланс' if user_lang == 'ru' else 'Available balance'
        limit_label = 'Предел' if user_lang == 'ru' else 'Limit'

        report_parts = []
        report_parts.append(f'<b>{stats["title"][i]}</b> ({category_subcategory})')
        report_parts.append(f'{current_period_label}: {period_range}')
        if stats['total_end'][i] is not None:
            end_date_label = 'Действителен до' if user_lang == 'ru' else 'Valid until'
            end_date = stats['total_end'][i].strftime('%d.%m.%Y')
            report_parts.append(f'{end_date_label}: {end_date}')

        cumulative_label = ' (накопительный)' if user_lang == 'ru' else ' (cumulative)'
        balance_string = f'{balance_label}: {stats["balance"][i]}'
        if stats['cumulative'][i]:
            balance_string += cumulative_label
        report_parts.append(balance_string)
        report_parts.append(f'{limit_label}: {stats["limit"][i]}')

        report_text = '\n'.join(report_parts)
        descriptions.append(report_text)

    report_text = '\n\n'.join(descriptions)
    return report_text, graph

