from sqlalchemy import select
from aiogram.utils.keyboard import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import ExpenseCategory, ExpenseSubcategory, ExpenseLimit, ExpenseLimitPeriod
from configs import async_sess_maker


def one_button_keyboard(labels, callback_data, user_language):
    """
    Generates one button keyboard with specified label and callback data.

    Args:
        labels (tuple[str, str]): Russian label, english label.
        callback_data (str): Callback data for the only button.
        user_language (str): User language to select label.

    Returns:
        InlineKeyboardMarkup: Keyboard markup.
    """
    # Create button
    button_text = labels[0] if user_language == 'ru' else labels[1]
    button = InlineKeyboardButton(text=button_text, callback_data=callback_data)
    # Create keyboard
    skip_keyboard = InlineKeyboardBuilder()
    skip_keyboard.add(button)

    return skip_keyboard.as_markup()


def binary_keyboard(user_language_code, first_button_data, second_button_data):
    """
    Generates boolean keyboard with provided labels and callback data.

    Args:
        user_language_code (str): User language to select labels.
        first_button_data (tuple[str, str, str]): Russian label, english label, callback data.
        second_button_data (tuple[str, str, str]): Russian label, english label, callback data.
    Returns:
        InlineKeyboardMarkup: Keyboard markup.
    """
    # Create yes button
    label_1 = first_button_data[0] if user_language_code == 'ru' else first_button_data[1]
    button_1 = InlineKeyboardButton(text=label_1, callback_data=first_button_data[2])
    # Create no button
    label_2 = second_button_data[0] if user_language_code == 'ru' else second_button_data[1]
    button_2 = InlineKeyboardButton(text=label_2, callback_data=second_button_data[2])

    # Pack everything into keyboard
    keyboard = InlineKeyboardBuilder()
    keyboard.add(button_1, button_2)

    return keyboard.as_markup()


def multi_button_keyboard(user_lang, buttons_data, one_row_count=2):
    """
    Generates multiple button keyboard with specified labels and callback data.

    Args:
        user_lang (str): User language to select labels.
        buttons_data (tuple[tuple[str, str, str]]): Russian label, english label, callback data.
        one_row_count (int): Number of buttons in one row to adjust layout.

    Returns:
        InlineKeyboardMarkup: Keyboard markup.
    """
    keyboard = InlineKeyboardBuilder()

    for button in buttons_data:
        text = button[0] if user_lang == 'ru' else button[1]
        button = InlineKeyboardButton(text=text, callback_data=button[2])
        keyboard.add(button)

    keyboard.adjust(one_row_count)
    return keyboard.as_markup()


async def categories_keyboard(user_language_code):
    """
    Generates categories keyboard with labels and callback data from database.

    Button labels language is dependent on ``user_language_code``. If specified language is not supported,
    english is used. Each button callback data is build according to template: ``category:int`` where int
    is category id in database.

    Args:
        user_language_code (str): User language.

    Returns:
        InlineKeyboardMarkup: Keyboard markup.
    """
    # Get dict of categories from DB
    categories = await ExpenseCategory.get_all_categories()

    # Create keyboard builder
    categories_keyboard = InlineKeyboardBuilder()
    # Iterate through categories dict and build keyboard
    for category_id, category_data in categories.items():
        try:
            button_text = category_data[user_language_code]
        except KeyError:
            button_text = category_data['en']
        button_callback = f'category:{category_id}:{button_text}'
        button = InlineKeyboardButton(text=button_text, callback_data=button_callback)
        categories_keyboard.add(button)
    # Adjust layout
    categories_keyboard.adjust(2)

    return categories_keyboard.as_markup()


async def subcategories_keyboard(category, user_language_code, end_button=False):
    """
    Generates subcategories keyboard with labels and callback data from database.

    Button labels are dependent on user language preference, english is used by default. Each button
    callback data is build according to template: ``subcategory:int`` where int is subcategory id in database.
    Button with callback data ``back`` is added to allow user get back to category selection.

    Args:
        category (ExpenseCategory | int): Expense Category object or category id value to query subcategories.
        user_language_code (str): User language.
        end_button (bool): Whether end button is enabled or not.

    Returns:
        InlineKeyboardMarkup: Keyboard markup.
    """
    # Get subcategories data from DB
    subcategories = await ExpenseSubcategory.get_by_category(category=category)

    # Create keyboard
    keyboard = InlineKeyboardBuilder()
    for subcategory_id, subcategory_data in subcategories.items():
        try:
            button_text = subcategory_data[user_language_code]
        except KeyError:
            button_text = subcategory_data['en']
        button_callback = f'subcategory:{subcategory_id}:{button_text}'
        button = InlineKeyboardButton(text=button_text, callback_data=button_callback)
        keyboard.add(button)
    # Add "back to categories" button
    back_to_categories_text = 'Назад к категориям' if user_language_code == 'ru' else 'Back to categories'
    back_button = InlineKeyboardButton(text=back_to_categories_text, callback_data='back')
    keyboard.add(back_button)

    if end_button:
        end_button_text = 'Сохранить' if user_language_code == 'ru' else 'Save'
        end_button_ = InlineKeyboardButton(text=end_button_text, callback_data='end')
        keyboard.add(end_button_)

    # Adjust markup
    keyboard.adjust(2)

    return keyboard.as_markup()


async def expense_limits_keyboard(user_id, user_lang, cancel_button=True):
    """
    Generates expense limits keyboard with labels and callback data from database.

    Each button is called according to expense limit user title, same is used for callback data.
    Cancel button can be added at the end of keyboard creation, if cancel_button = True. If cancel button
    is added, its callback data is `cancel_limit`.

    Args:
        user_id (int): User id.
        user_lang (str): User language.
        cancel_button (bool): If cancel button should be added.

    Returns:
        InlineKeyboardMarkup | None: Keyboard markup, if any expense limit exists, otherwise None.
    """
    # Get user limits from database
    user_limits = await ExpenseLimit.select_by_user_id(user_id=user_id)
    if len(user_limits) == 0:
        return None

    # Create keyboard
    keyboard = InlineKeyboardBuilder()
    for limit in user_limits:
        button_text = limit[0].__getattribute__('user_title')
        button = InlineKeyboardButton(text=button_text, callback_data=button_text)
        keyboard.add(button)

    # Add cancel button, if required
    if cancel_button:
        cancel_button_text = 'Отмена' if user_lang == 'ru' else 'Cancel'
        button = InlineKeyboardButton(text=cancel_button_text, callback_data='cancel_limit')
        keyboard.add(button)

    # Adjust markup
    keyboard.adjust(1)

    return keyboard.as_markup()


async def period_keyboard(user_language_code):
    """
    Generates expense limit period options inline keyboard.

    Button labels are dependent on user language preference, english is used by default. Each button callback data
    is constructed by template: ``period:int`` where int is period id: 1 = 7 days, 2 = 30 days, 3 = 365 days.

    Args:
        user_language_code (str): User language.

    Returns:
        InlineKeyboardMarkup: Keyboard markup.
    """
    # Query all limits
    query = select(ExpenseLimitPeriod).order_by(ExpenseLimitPeriod.period.asc())
    async with async_sess_maker() as session:
        data = await session.execute(query)
    existing_limits = data.scalars()

    # Create buttons
    buttons = []
    for lim in existing_limits:
        button_text = f'{lim.period} дней' if user_language_code == 'ru' else f'{lim.period} days'
        button = InlineKeyboardButton(text=button_text, callback_data=f'period:{lim.id}:{lim.period}')
        buttons.append(button)

    # Create keyboard
    keyboard = InlineKeyboardBuilder()
    keyboard.add(*buttons)

    # Adjust markup
    keyboard.adjust(1)

    return keyboard.as_markup()

