import re
import datetime as dt

from shapely.geometry.point import Point
from aiogram.types import Location
from loguru import logger

from bot.routers import MessageTexts as MT


def money_amount_from_user_message(user_message_text, user_lang):
    """
    Tries to convert message text into positive float.

    Args:
        user_message_text (str): User message text.
        user_lang (str): User language.

    Returns:
        tuple[float, None] | tuple[None, str]: Value, None or None, error text
    """
    user_message_text = user_message_text.replace(',', '.')
    try:
        money_amount = float(user_message_text)
        if money_amount > 0:
            return money_amount, None
        else:
            m_texts = MT(
                ru_text='К сожалению, сумма не может быть негативной',
                en_text='Sorry, money amount can\'t be negative'
            )
            return None, m_texts.get(user_lang)
    except (ValueError, Exception):
        m_texts = MT(
            ru_text='Пожалуйста, пришлите сумму (например, 123.45 или 123) без какой-либо другой информации',
            en_text='Please send money amount (ex. 123.45 or 123) without any other information'
        )
        return None, m_texts.get(user_lang)


def date_is_in_past(date: dt.date | dt.datetime):
    """
    Checks if date is today or earlier.

    Args:
        date (dt.date | dt.datetime): Date to check.

    Returns:
        bool: Comparison result.
    """
    try:
        return dt.date.today() >= date
    except TypeError:
        pass
    try:
        return dt.datetime.now() >= date
    except TypeError:
        return False


def date_check_result(date, past, user_lang):
    """
    For dates that are expected to refer to the past checks if they are in the past.
    For dates that are expected to refer to the future checks if they are in the future.

    Args:
        date (dt.date | dt.datetime): Date to check.
        past (bool): True if past check.
        user_lang (str): User language.

    Returns:
        tuple[dt.date, None] | tuple[None, str]: Date or None, None or error text.
    """
    date_passed = date_is_in_past(date)
    if past:
        m_texts = MT(
            ru_text='Эта дата ещё не наступила. Пожалуйста, пришлите корректную дату из прошлого',
            en_text='This date has not happened yet. Please, send correct one from the past'
        )
        return (date, None) if date_passed else (None, m_texts.get(user_lang))
    else:
        m_texts = MT(
            ru_text='Эта дата уже наступила. Пожалуйста, пришлите корректную дату из будущего',
            en_text='This date has already happened. Please, send correct one from the future'
        )
        return (date, None) if not date_passed else (None, m_texts.get(user_lang))


def event_date_from_user_message(user_message_text, user_lang, past=True):
    """
    Tries to convert message text to date in past or today.

    Args:
        user_message_text (str): User message text.
        user_lang (str): User language.
        past (bool): True if past check.

    Returns:
        tuple[dt.date, None] | tuple[None, str]: Date or None.
    """
    try:
        # Immediate convert
        event_date = dt.datetime.strptime(user_message_text, '%d.%m.%Y').date()
        return date_check_result(event_date, past, user_lang)
    except ValueError:
        # Extract date string and convert it
        date_pattern = r'(\d{1,2}\.\d{1,2}\.\d{4})'
        try:
            date_string_from_message = re.search(date_pattern, user_message_text).group(1)
            event_date = dt.datetime.strptime(date_string_from_message, '%d.%m.%Y').date()
            return date_check_result(event_date, past, user_lang)
        except (AttributeError, Exception) as e:
            logger.error(e)
            # Failed both times
            m_texts = MT(
                ru_text='Пожалуйста, пришлите дату в правильном формате (например, 01.12.2023)',
                en_text='Please send correctly formatted date (ex. 01.12.2023)'
            )
            return None, m_texts.get(user_lang)


def event_datetime_from_user_message(user_message_text, user_lang, past=True):
    """
    Tries to convert message text to datetime in past or today.

    Args:
        user_message_text (str): User message text.
        user_lang (str): User language.
        past (bool): True if past check.

    Returns:
        tuple[dt.datetime, None] | tuple[None, str]: Date or None.
    """
    try:
        event_datetime = dt.datetime.strptime(user_message_text, '%d.%m.%Y %H:%M')
        return date_check_result(event_datetime, past, user_lang)
    except (ValueError, Exception):
        try:
            datetime_pattern = r'(\d{1,2}\.\d{1,2}\.\d{4} \d{1,2}\:\d{1,2})'
            event_datetime_string = re.search(datetime_pattern, user_message_text).group(1)
            event_datetime = dt.datetime.strptime(event_datetime_string, '%d.%m.%Y %H:%M')
            return date_check_result(event_datetime, past, user_lang)
        except (AttributeError, Exception) as e:
            logger.error(e)
            m_texts = MT(
                ru_text='Пожалуйста, пришлите дату и время в правильном формате (например, 01.12.2023 23:59)',
                en_text='Please send correctly formatted date and time (ex. 01.12.2023 23:15)'
            )
            return None, m_texts.get(user_lang)


def tg_location_to_geometry(tg_location):
    """
    Converts telegram location to shapely.geometry.point.

    Args:
        tg_location (Location): Telegram location.

    Returns:
        Point: Shapely point.
    """
    return Point(tg_location.longitude, tg_location.latitude)
