import os.path

from dotenv import dotenv_values


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SECRETS_PATH = os.path.join(BASE_DIR, '.env')

secrets = dotenv_values(SECRETS_PATH)
DEBUG = True
DB_HOST = secrets['DB_HOST']
DB_PORT = secrets['DB_PORT']
DB_USER_NAME = secrets['DB_USER_NAME']
DB_PASSWORD = secrets['DB_PASSWORD']

if DEBUG:
    DB_NAME = secrets['DB_NAME_DEV']
else:
    DB_NAME = secrets['DB_NAME_PROD']

TEST_DB_NAME = secrets['DB_NAME_TEST']

BOT_TOKEN = secrets['BOT_TOKEN']
BOT_ADMIN = secrets['BOT_ADMIN']

