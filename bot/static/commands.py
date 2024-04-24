from aiogram.types import BotCommand


commands = {
    'add_expense': {
        'en': 'Add new expense',
        'ru': 'Добавить новый расход',
        'en_long': "Log new expense: money amount, category of expense, date and time, location (optional). /abort "
                   "command stops the process and erases temp data (previously logged expenses won't change).",
        'ru_long': "Добавить новый расход: сумма, категория расхода, дата и время, местоположение (опционально). "
                   "Команда /abort прервёт процесс и удалит все временные данные (сохранённые ранее расходы "
                   "не пострадают).",
    },
    'add_income': {
        'en': 'Add new income',
        'ru': 'Добавить новый доход',
        'en_long': '',
        'ru_long': '',
    },
    'add_expense_limit': {
        'en': 'Add new expense limit for subcategory',
        'ru': 'Добавить предел расходов по подкатегории',
        'en_long': '',
        'ru_long': '',
    },
    'help': {
        'en': 'Get help on bot functions and commands',
        'ru': 'Справка о функциях и командах бота',
        'en_long': '',
        'ru_long': '',
    },
    'about': {
        'en': 'About the project',
        'ru': 'О проекте',
        'en_long': '',
        'ru_long': '',
    },
    'abort': {
        'en': 'Abort current process and erase temp data',
        'ru': 'Прервать текущий процесс и удалить временные данные',
        'en_long': '',
        'ru_long': '',
    },
    'delete_my_data': {
        'en': 'Delete all one-related data from database',
        'ru': 'Удалить все связанные с пользователем данные из базы данных',
        'en_long': '',
        'ru_long': '',
    }
}


# List of commands applied to all languages
def en_commands_list() -> list[BotCommand]:
    commands_en = []
    for command_text, description_dict in commands.items():
        command = BotCommand(command=command_text, description=description_dict['en'])
        commands_en.append(command)
    return commands_en


# List of commands applied to russian language
def ru_commands_list() -> list[BotCommand]:
    commands_ru = []
    for command_text, description_dict in commands.items():
        command = BotCommand(command=command_text, description=description_dict['ru'])
        commands_ru.append(command)
    return commands_ru
