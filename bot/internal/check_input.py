"""
Package contains scripts that are used to check user input and extract values from message texts.

+ ``money_amount_from_user_message`` function tries to convert user message text to float value.
+ ``date_is_in_past`` function checks that date or datetime instance provided is earlier than current date and time.
+ ``event_date_from_user_message`` function tries to convert user message text to date instance.
+ ``event_datetime_from_user_message`` function tries to convert user message text to datetime instance.
+ ``tg_location_to_geometry`` function converts telegram location instance into shapely point instance.
"""
import logging
import re
import datetime as dt

from shapely.geometry.point import Point
from aiogram.types import Location


def money_amount_from_user_message(user_message_text: str) -> [float | None, None | str]:
    """
    Tries to convert message text into positive float.
    :param user_message_text: Message text.
    :return: Positive float or None.
    """
    user_message_text = user_message_text.replace(',', '.')
    try:
        money_amount = float(user_message_text)
        if money_amount > 0:
            return money_amount, None
        else:
            return None, 'Sorry, money amount cannot be negative.'
    except (ValueError, Exception):
        return None, 'Please send a number without, like 123.45 or 123'


def date_is_in_past(date: dt.date | dt.datetime) -> bool:
    """
    Checks if date is today or earlier.
    :param date: Date or datetime value to compare to now.
    :return: Comparison result.
    """
    try:
        return dt.date.today() >= date
    except TypeError:
        pass
    try:
        return dt.datetime.now() >= date
    except TypeError:
        return False


def date_check_result(date: dt.date | dt.datetime, past: bool):
    date_passed = date_is_in_past(date)
    if past:
        return (date, None) if date_passed else (None, 'This date has not happened yet')
    else:
        return (date, None) if not date_passed else (None, 'This date has happened already')


def event_date_from_user_message(user_message_text: str, past: bool = True) -> [dt.date | None, None | str]:
    """
    Tries to convert message text to date in past or today.
    :param user_message_text: Message text.
    :param past: Date must be in the past.
    :return: Date or None.
    """
    try:
        # Immediate convert
        event_date = dt.datetime.strptime(user_message_text, '%d.%m.%Y').date()
        return date_check_result(event_date, past)
    except ValueError:
        # Extract date string and convert it
        date_pattern = r'(\d{1,2}\.\d{1,2}\.\d{4})'
        try:
            date_string_from_message = re.search(date_pattern, user_message_text).group(1)
            event_date = dt.datetime.strptime(date_string_from_message, '%d.%m.%Y').date()
            return date_check_result(event_date, past)
        except (AttributeError, Exception) as e:
            logging.error(e)
            # Failed both times
            return None, 'Please send a correct date in format 01.12.2023'


def event_datetime_from_user_message(user_message_text: str, past: bool = True) -> [dt.datetime | None, None | str]:
    """
    Tries to convert message text to datetime in past or today.
    :param user_message_text: User message text.
    :param past: Date must be in the past.
    :return: Datetime or None.
    """
    try:
        event_datetime = dt.datetime.strptime(user_message_text, '%d.%m.%Y %H:%M')
        return date_check_result(event_datetime, past)
    except (ValueError, Exception):
        try:
            datetime_pattern = r'(\d{1,2}\.\d{1,2}\.\d{4} \d{1,2}\:\d{1,2})'
            event_datetime_string = re.search(datetime_pattern, user_message_text).group(1)
            event_datetime = dt.datetime.strptime(event_datetime_string, '%d.%m.%Y %H:%M')
            return date_check_result(event_datetime, past)
        except (AttributeError, Exception) as e:
            logging.error(e)
            return None, 'Please send a correct date in format 01.12.2023 23:15'


def tg_location_to_geometry(tg_location: Location) -> Point:
    return Point(tg_location.longitude, tg_location.latitude)
