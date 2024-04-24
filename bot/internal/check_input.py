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

from bot.static.messages import CHECKS_MESSAGES


def money_amount_from_user_message(user_message_text: str, user_lang: str) -> [float | None, None | str]:
    """
    Tries to convert message text into positive float.
    :param user_message_text: Message text.
    :param user_lang: User language.
    :return: Positive float or None.
    """
    user_message_text = user_message_text.replace(',', '.')
    try:
        money_amount = float(user_message_text)
        if money_amount > 0:
            return money_amount, None
        else:
            return None, CHECKS_MESSAGES['negative_money_amount'][user_lang]
    except (ValueError, Exception):
        return None, CHECKS_MESSAGES['incorrect_money_amount'][user_lang]


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


def date_check_result(date: dt.date | dt.datetime, past: bool, user_lang: str):
    """
    For dates that are expected to refer to the past checks if they are in the past.
    For dates that are expected to refer to the future checks if they are in the future.
    :param date: Date to check.
    :param past: Expected to be in past?
    :param user_lang: User language for error text.
    :return: Date or None, None or error text.
    """
    date_passed = date_is_in_past(date)
    if past:
        return (date, None) if date_passed else (None, CHECKS_MESSAGES['future_date'][user_lang])
    else:
        return (date, None) if not date_passed else (None, CHECKS_MESSAGES['past_date'][user_lang])


def event_date_from_user_message(user_message_text: str, user_lang: str, past: bool = True) -> [dt.date | None, None | str]:
    """
    Tries to convert message text to date in past or today.
    :param user_message_text: Message text.
    :param past: Date must be in the past.
    :param user_lang: User language for error text.
    :return: Date or None.
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
            logging.error(e)
            # Failed both times
            return None, CHECKS_MESSAGES['incorrect_date_format'][user_lang]


def event_datetime_from_user_message(user_message_text: str, user_lang: str, past: bool = True) -> [dt.datetime | None, None | str]:
    """
    Tries to convert message text to datetime in past or today.
    :param user_message_text: User message text.
    :param past: Date must be in the past.
    :param user_lang: User language for error text.
    :return: Datetime or None.
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
            logging.error(e)
            return None, CHECKS_MESSAGES['incorrect_datetime_format'][user_lang]


def tg_location_to_geometry(tg_location: Location) -> Point:
    return Point(tg_location.longitude, tg_location.latitude)
