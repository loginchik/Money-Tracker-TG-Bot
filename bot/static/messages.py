DELETE_ROUTER_MESSAGES = {
    'nothing_to_delete': {
        'ru': 'Вы не зарегистрированы, так что нет данных для удаления',
        'en': 'You are not registered, so there is no data to delete.'
    },
    'confirmation': {
        'ru': 'Вы уверены? Данные удаляются тут же и безвозвратно, '
              '<b>действие не может быть отменено</b>',
        'en': 'Are you sure? Data will be deleted immediately and forever. '
              '<b>The action cannot be undone</b>'
    },
    'success': {
        'ru': 'Все данные, связанные с вами, удалены. Всего хорошего!',
        'en': 'All data associated with you is deleted. Thank you!'
    },
    'error': {
        'ru': 'К сожалению, произошла внутренняя ошибка, данные сохранены. '
              'Пожалуйста, попробуйте позже',
        'en': 'Unfortunately, internal error occurred, data is still saved. '
              'Please try again.'
    },
    'cancel': {
        'ru': 'Данные сохранены. Спасибо, что остаётесь с нами!',
        'en': 'Your data is kept in safe. Thank you for staying with us!'
    }
}


GENERAL_ROUTER_MESSAGES = {
    'hello': {
        'ru': 'Привет!',
        'en': 'Hello!',
    },
    'help_heading': {
        'ru': 'Доступные команды',
        'en': 'Commands available',
    },
    'about': {
        'ru': 'О боте!',
        'en': 'About!',
    },
}


NEW_ROUTER_MESSAGES = {
    'aborted': {
        'ru': 'Процесс прекращён, временные данные удалены',
        'en': 'Process is aborted, temp data is deleted'
    },
    'preferred_language': {
        'ru': 'Выберите предпочтительный язык',
        'en': 'Choose preferred language',
    },
    'registration_agreement': {
        'ru': 'Чтобы пользоваться ботом, вам необходимо зарегистрироваться. Все пользовательские данные хранятся в '
              'изолированных таблицах, другие пользователи не смогут получить доступ к вашим данным точно так же, '
              'как вы не сможете получить доступ к данным других пользователей. Вы всегда сможете удалить связанные '
              'с вами данные командой /delete_my_data command.\n\nСоздать аккаунт?',
        'en': 'To access bot functionality, you must register. All data is kept in isolated tables, other users won\'t'
              'have access to your data same as you won\'t have access to their data. You are always able to delete '
              'all the data associated with you with /delete_my_data command.\n\nWould you like to create an account?'
    },
    'registration_success': {
        'ru': 'Аккаунт успешно создан',
        'en': 'Account created successfully',
    },
    'registration_fail': {
        'ru': 'Что-то пошло не так. Пожалуйста, попробуйте позже',
        'en': 'Something went wrong. Please try again later'
    },
    'registration_cancel': {
        'ru': 'К сожалению, для доступа к боту необходимо зарегистрироваться :(',
        'en': 'Sorry, you have to register to access the bot :('
    },
    'after_registration': {
        'ru': f'Аккаунт успешно создан. Теперь вам доступен функционал бота. '
              'Вы присылали команду {}. Отправьте её ещё раз, теперь она сработает',
        'en': f'Account created successfully. Now you can access bot functionality. '
              'Previously you sent a command {}. Send it again, now it will work',
    },

    'expense_money_amount': {
        'ru': '1/5. Пожалуйста, пришлите сумму (формат: 123.45 или 123)',
        'en': '1/5. Please, send money amount (format: 123.45 or 123)'
    },
    'expense_category': {
        'ru': '2/5. Выберите категорию',
        'en': '2/5. Choose expense category'
    },
    'incorrect_category': {
        'ru': 'Пожалуйста, выберите категорию',
        'en': 'Please, choose category'
    },
    'expense_subcategory': {
        'ru': '3/5. Выберите подкатегорию',
        'en': '3/5. Choose expense subcategory'
    },
    'incorrect_subcategory': {
        'ru': 'Пожалуйста, выберите подкатегорию',
        'en': 'Please, choose subcategory'
    },
    'expense_datetime': {
        'ru': '4/5. Пришлите дату и время совершения покупки (формат: 01.12.2025 23:15)',
        'en': '4/5. Send date and time of expense (format: 01.12.2023 23:15)'
    },
    'expense_location': {
        'ru': '5/5. Если хотите, пришлите локацию места, где совершалась покупка, либо нажмите '
              'кнопку, чтобы пропустить и продолжить',
        'en': '5/5. If you wish, send location of place where you made a purchase.'
              'Or press button to skip and continue'
    },
    'expense_saved': {
        'ru': 'Данные о расходе успешно сохранены',
        'en': 'Expense data saved successfully'
    },
    'expense_save_error': {
        'ru': 'К сожалению, что-то пошло не так. Данные не сохранены. Пожалуйста, попробуйте ещё раз позднее',
        'en': 'Unfortunately, something went wrong. Data is not saved. Please try again later'
    },

    'income_amount': {
        'ru': '1/3. Пожалуйста, пришлите сумму (формат: 123.45 или 123)',
        'en': '1/3. Please, send money amount (format: 123.45 or 123)'
    },
    'active_status': {
        'ru': '2/3. Это активный или пассивный доход?\n\n'
              'Пассивный доход — это доход, для получения которого не требуется значительных усилий',
        'en': '2/3. Is the income active or passive?\n\n'
              'Passive income is revenue that takes negligible effort to acquire'
    },
    'income_date': {
        'ru': '3/3. Пришлите дату получения дохода (формат: 01.12.2023)',
        'en': '3/3. Send date of income (format: 01.12.2023)'
    },
    'income_saved': {
        'ru': 'Данные о доходе успешно сохранены',
        'en': 'Income data saved successfully'
    },
    'income_save_error': {
        'ru': 'К сожалению, что-то пошло не так. Данные не сохранены. Пожалуйста, попробуйте ещё раз позже',
        'en': 'Unfortunately, something went wrong. Data is not saved. Please try again'
    },

    'expense_limit_title': {
        'ru': f'1/8. Пожалуйста, пришлите название нового предела расходов. Оно должно быть уникальным '
              f'и не длиннее 100 символов. ',
        'en': f'1/8. Please, send expense limit title. It should be unique and no more than 100 characters length. '
    },
    'expense_limit_title_too_long': {
        'ru': 'Это название слишком длинное. Пожалуйста, пришлите корректное',
        'en': 'This title is too long. Please, send correct one'
    },
    'expense_limit_existent_limits': {
        'ru': 'У вас уже есть пределы с названиями {}',
        'en': 'You already have limits named {}'
    },
    'expense_limit_category': {
        'ru': '2/8. Предел расходов связывается с подкатегорией расходов. Выберите категорию, чтобы'
              'получить варианты подкатегорий на следующем шаге',
        'en': '2/8. Expense limit is linked with expense subcategory. '
              'Choose a category to get subcategory options in the next step'
    },
    'expense_limit_subcategory': {
        'ru': '3/8. Выберите подкатегорию',
        'en': '3/8. Choose subcategory'
    },
    'expense_limit_period': {
        'ru': '4/8. Предел расходов сбрасывается раз в определённый период времени. '
              'Как долго должен длиться один период?',
        'en': '4/8. Expense limit is reset after some period of time. How long should one limit last?'
    },
    'expense_limit_period_start': {
        'ru': '5/8. Когда начать применять предел? Вы можете выбрать с помощью кнопок или прислать дату вручную'
              '(формат: 01.12.2023).',
        'en': '5/8. When to start applying expense limit? You can choose by buttons or send a date manually '
              '(format: 01.12.2023).'
    },
    'expense_limit_value': {
        'ru': '6/8. Какую максимальную сумму вы бы хотели тратить на подкатегорию в один период? '
              '(формат: 123.45 или 123)',
        'en': '6/8. What is the maximum amount of money you would like to spend for the subcategory in one period?'
              '(format: 123.45 or 123)'
    },
    'expense_limit_end_date': {
        'ru': '7/8. Если хотите, установите дату окончания действия предела расходов. После этой даты предел расходов '
              'будет автоматически удалён (формат: 01.12.2023). Нажмите кнопку, чтобы пропустить и продолжить',
        'en': '7/8. If you wish, set the end date of expense limit. After this date expense limit will be deleted '
              'automatically (format: 01.12.2023). Press button to skip and continue'
    },
    'expense_limit_cumulative': {
        'ru': '8/8. Вы хотите сбрасывать доступный баланс предела, когда период заканчивается, или копить баланс? '
              'Если предел накопительный, то когда у вас останется, например, 10 от текущего периода в следующем '
              'периоде баланс будет 10 + максимальная сумма, которую вы установили на шаге 6',
        'en': '8/8. Do you want to reset available balance to limit value when period ends or to accumulate it?' 
              'Cumulative means that if you have for example 10 left from the period, new period\'s balance will be '
              '10 + max amount you set on step 6'
    },
    'expense_limit_saved': {
        'ru': 'Предел расходов успешно создан',
        'en': 'Expense limit created successfully'
    },
    'expense_limit_save_error': {
        'ru': 'К сожалению, что-то пошло не так. Предел расходов не создан. Пожалуйста, попробуйте ещё раз позже',
        'en': 'Unfortunately, something went wrong. Expense limit is not created. Please, try again later'
    },

    'expense_limit_stats': {
        'ru': '{} ({} дней до конца периода)\n'
              '|{}| ({}%, {} осталось)',
        'en': '{} ({} days until period end)\n'
              '|{}| ({}%, {} left)'
    }
}


CHECKS_MESSAGES = {
    'negative_money_amount': {
        'ru': 'К сожалению, сумма не может быть негативной',
        'en': 'Sorry, money amount can\'t be negative'
    },
    'incorrect_money_amount': {
        'ru': 'Пожалуйста, пришлите сумму (например, 123.45 или 123) без какой-либо другой информации',
        'en': 'Please send money amount (ex. 123.45 or 123) without any other information'
    },
    'future_date': {
        'ru': 'Эта дата ещё не наступила. Пожалуйста, пришлите корректную дату из прошлого',
        'en': 'This date has not happened yet. Please, send correct one from the past'
    },
    'past_date': {
        'ru': 'Эта дата уже наступила. Пожалуйста, пришлите корректную дату из будущего',
        'en': 'This date has already happened. Please, send correct one from the future'
    },
    'incorrect_date_format': {
        'ru': 'Пожалуйста, пришлите дату в правильном формате (например, 01.12.2023)',
        'en': 'Please send correctly formatted date (ex. 01.12.2023)'
    },
    'incorrect_datetime_format': {
        'ru': 'Пожалуйста, пришлите дату и время в правильном формате (например, 01.12.2023 23:59)',
        'en': 'Please send correctly formatted date and time (ex. 01.12.2023 23:15)'
    }
}