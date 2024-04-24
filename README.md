# Money Tracker Bot and Web App

Python-based Telegram bot that can be helpful in tracking one's expenses and incomes. Requires a Postgres database
configured and aiogram to run in asynchronous mode. Function and triggers for DB automatic configurations can be 
found in [sql scripts folder](db/db_setup).

Requirements list: [requirements.txt](requirements.txt)

## Project structure 

```
root
├── bot
│   ├── filters
│   │   ├── __init__.py
│   │   └── user_exists.py
│   ├── internal
│   │   ├── __init__.py
│   │   └── check_input.py
│   ├── keyboards
│   │   ├── __init__.py
│   │   ├── bool_keyboard.py
│   │   ├── categories_keyboard.py
│   │   ├── limit_period_keyboard.py
│   │   ├── period_start_keyboard.py
│   │   ├── registration_keyboard.py
│   │   ├── skip_keyboard.py
│   │   ├── subcategories_keyboard.py
│   │   └── today_keyboard.py
│   ├── middleware
│   │   ├── __init__.py
│   │   └── user_language.py
│   ├── routers
│   │   ├── __init__.py
│   │   ├── delete_router.py
│   │   ├── general_router.py
│   │   ├── main_router.py
│   │   └── new_router.py
│   ├── states
│   │   ├── __init__.py
│   │   ├── new_expense.py
│   │   ├── new_expense_limit.py
│   │   ├── new_income.py
│   │   └── registration.py
│   ├── static 
│   │   ├── __init__.py
│   │   ├── commands.py
│   │   ├── messages.py
│   │   └── user_languages.py 
│   └── __init__.py
├── db
│   ├── db_setup
│   │   ├── functions
│   │   └── triggers 
│   ├── .env
│   ├── __init__.py
│   ├── connection.py
│   ├── expense_limit_operations.py
│   ├── expense_operations.py
│   ├── income_operations.py
│   └── user_operations.py
├── bot.py
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```