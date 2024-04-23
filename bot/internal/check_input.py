import re
import datetime as dt

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


def date_is_in_past(date: dt.date) -> bool:
    """
    Checks if date is today or earlier.
    :param date: Date to check.
    :return: Comparison result.
    """
    return dt.date.today() >= date


def event_date_from_user_message(user_message_text: str) -> [dt.date | None, None | str]:
    """
    Tries to convert message text to date in past or today.
    :param user_message_text: Message text.
    :return: Date or None.
    """
    try:
        # Immediate convert
        event_date = dt.datetime.strptime(user_message_text, '%d.%m.%Y').date()
        if date_is_in_past(event_date):
            return event_date, None
        else:
            return None, 'This date has not happened yet'
    except ValueError:
        # Extract date string and convert it
        date_pattern = r'(\d{1,2}\.\d{1,2}\.\d{4})'
        try:
            date_string_from_message = re.search(date_pattern, user_message_text).group(1)
            event_date = dt.datetime.strptime(date_string_from_message, '%d.%m.%Y').date()
            if date_is_in_past(event_date):
                return event_date, None
            else:
                return None, 'This date has not happened yet'
        except (AttributeError, Exception):
            # Failed both times
            return None, 'Please send a correct date in format 01.12.2023'
