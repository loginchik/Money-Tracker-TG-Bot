# Money Tracker Bot and Web App

A Python-based Telegram bot to track expenses and revenues. 

## Inspiration

When I started earning and spending my own money, I faced the problem of keeping track of the spent money. 
I tried many ways to track expenses, starting from Google Sheet, ending with special applications. Every time I faced 
the same problem: I was too lazy to spend even a few minutes opening the sheet or the application to enter all the data. 
Google Sheet is inconvenient to edit from mobile phones and applications have limitations. Finally, I decided to switch 
to Telegram as this was the application I was using the most. That is how the idea appeared. 

I started with the simplest bot, which could only add new records to the database. Later I decided to add an expense 
limits function to help myself manage some categories of expenses that I would prefer not to waste too much money on. 
After that, I understood that there is no problem giving some basic analysis of recorded data straight via bot. Also, 
I created a basic mechanism to track incomes. That is how the idea developed.

## How it works

### Data storing 

All the data is stored in PostgreSQL database with PostGIS extension configured. Categories, subcategories and 
expense limit periods are constant and the same for all users, whilst expenses, incomes and expense limits are stored 
separately. The bot is based on aiogram modules. 

### Users' data management and privacy 

Once users wants to add anything via `/add` command, the bot offers to create an account. This means that the bot doesn't 
start storing any of the user data unless the user allows it. Before the user creates an account, bot messages in russian 
or english depending on the Telegram language setting; after creating the account bot messages in a user-specified language 
(Russian or English, other languages are not supported yet). 

After creating the account the user can add expenses, incomes, create expense limits (`/add`), get statistics (`/stats`) 
and export all recorded revenues and expenses (`/export_my_data`). If one would like to, there is an option to delete 
all user-related data from the database via `/delete_my_data` command. After deleting all one-related data via command 
bot messages in Russian or English depending on Telegram language setting available from Telegram API.

### Expenses 

Expense is linked to a static expense subcategory. The expense subcategory is linked to the expense category. Expenses can 
be added via `/add` command after submitting the registration agreement. Each expense has a datetime stamp 
(when it happened, not when it was created), money amount, linked subcategory and location (optional). 

### Incomes 

Incomes have no links with static data. Incomes can be active or passive; have date stamp, money amount. 

### Expense limits 

Expense limits do not affect user's ability to add new expenses. Expense limit has a title, unique for the user, 
period (in days) or repetition, limit money amount value, current period start and end, expiration date, 
linked subcategories and cumulative status. One expense limit can be linked to max 5 subcategories. 
When the current period start date is before the current date, limit balance is reduced by relative expenses. 
Users can delete the existing expense limit via `/delete_expense_limit` command. 

Once created, the expense limit is managed automatically. When new expenses are created, linked to the same 
subcategories and actual on the moment of expense date and time value limits change their balance. The limit 
period ends, the balance is reset automatically on the next day (midnight in Moscow). When the limit expires, it is 
deleted automatically.


## Project structure 

```
.
├── bot
│   ├── internal
│   │   ├── __init__.py
│   │   ├── check_input.py
│   │   └── graphs.py
│   ├── routers
│   │   ├── __init__.py
│   │   ├── common_router.py
│   │   ├── delete_router.py
│   │   ├── export_router.py
│   │   ├── general_router.py
│   │   ├── new_router.py
│   │   └── stats_router.py
│   ├── static 
│   │   ├── __init__.py
│   │   ├── commands.json
│   │   ├── commands.py
│   │   ├── messages.py
│   │   └── user_languages.py 
│   ├── __init__.py
│   ├── filters.py
│   ├── fsm_states.py
│   ├── keyboards.py
│   └── middleware.py
├── db
│   ├── static
│   │   ├── categories.json
│   │   ├── limit_periods.json
│   │   └── subcategories.json 
│   ├── __init__.py
│   ├── shared_schema.py
│   └── user_based_schema.py
├── logs
├── temp
├── .env
├── .gitignore
├── bot.py
├── configs.py
├── LICENSE
├── poetry.lock
├── pyproject.toml
└── README.md
```