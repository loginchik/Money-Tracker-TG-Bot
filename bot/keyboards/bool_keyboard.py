from aiogram.utils.keyboard import InlineKeyboardMarkup, InlineKeyboardButton, InlineKeyboardBuilder


async def generate_bool_keyboard(user_language_code: str, true_labels: tuple[str, str, str] = ('Да', 'Yes', 'true'),
                                 false_labels: tuple[str, str, str] = ('Нет', 'No', 'false')) -> InlineKeyboardMarkup:
    """
    Generates boolean keyboard with provided labels and callback data.
    :param user_language_code: User language.
    :param true_labels: Russian label, english label, callback data.
    :param false_labels: Russian label, english label, callback data.
    :return: Keyboard markup.
    """

    yes_button = InlineKeyboardButton(text=true_labels[0] if user_language_code == 'ru' else true_labels[1],
                                      callback_data=true_labels[2])
    no_button = InlineKeyboardButton(text=false_labels[0] if user_language_code == 'ru' else false_labels[1],
                                     callback_data=false_labels[2])
    keyboard = InlineKeyboardBuilder()
    keyboard.add(yes_button, no_button)
    return keyboard.as_markup()
