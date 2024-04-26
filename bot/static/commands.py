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
        'en_long': "Log new income: money amount, active or passive mark, date. /abort command stops the process "
                   "and erases temp data (previously logged incomes won't change).",
        'ru_long': "Добавить новый доход: сумма, активный или пассивный, дата. Команда /abort прервёт процесс и "
                   "удалит все временные данные (сохранённые ранее доходы не пострадают).",
    },
    'add_expense_limit': {
        'en': 'Add new expense limit for subcategory',
        'ru': 'Добавить предел расходов по подкатегории',
        'en_long': "Add new expense limit. Expense limits don't affect expense logging but help to keep track "
                   "of expenses by subcategories. Expense limits are set for a specified period of time "
                   "(7/30/365 days). Expired limits are deleted automatically. /abort command stops the process "
                   "and erases temp data (previously created expense limits won't change).",
        'ru_long': "Добавить новый предел расходов, связанный с подкатегорией расходов. Пределы расходов не "
                   "ограничивают возможность вносить расходы, но помогают контролировать их. Пределы расходов "
                   "устанавливаются на определённый временной период (7/30/365 дней). Просроченные пределы удаляются"
                   "автоматически. Команда /abort прервёт процесс и удалит все временные данные (созданные ранее "
                   "пределы расходов не пострадают).",
    },
    'delete_expense_limit': {
        'en': 'Delete active expense limit.',
        'ru': 'Удалить предел расходов',
        'en_long': 'Delete active expense limit before it runs out of date',
        'ru_long': 'Удалить предел расходов до того, как он выйдет из срока годности',
    },
    'stats': {
        'en': 'Get statistics',
        'ru': 'Получить статистику',
        'en_long': 'Get statistics for account, expense limits, expenses from last 30 days.',
        'ru_long': 'Получить статистику о пользователе, пределах расходов, расходах за последние 30 дней'
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
        'en_long': 'Project goals and history.',
        'ru_long': 'История и цели проекта.',
    },
    'abort': {
        'en': 'Abort current process and erase temp data',
        'ru': 'Прервать текущий процесс и удалить временные данные',
        'en_long': '',
        'ru_long': '',
    },
    'export_my_data': {
        'en': 'Export all one-related expenses and incomes into files and send them via bot',
        'ru': 'Экспортировать все связанные с пользователем расходы и доходы в файлы и отправить их ботом',
        'en_long': 'Export all one-related expenses and incomes into files and send them via bot. If '
                   'files appear to be bigger than Telegram size limit, only the most recent records will be exported',
        'ru_long': 'Экспортировать все связанные с пользователем расходы и доходы в файлы и отправить их ботом. '
                   'Если файлы оказываются больше, чем позволяют лимиты Телеграма, экспортируются только наиболее'
                   'недавние записи',
    },
    'delete_my_data': {
        'en': 'Delete all one-related data from database',
        'ru': 'Удалить все связанные с пользователем данные из базы данных',
        'en_long': 'Delete all the user data. The action cannot be undone.',
        'ru_long': 'Удалить все данные пользователя. Действие необратимо.',
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
