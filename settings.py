import os.path
import datetime as dt

from dotenv import dotenv_values

base_dir = os.path.split(os.path.abspath(__file__))[0]
bot_secrets_path = os.path.join(base_dir, '.env')
db_secrets_path = os.path.join(base_dir, 'db', '.env')

bot_secrets = dotenv_values(bot_secrets_path)
db_secrets = dotenv_values(db_secrets_path)

log_filename = dt.datetime.now().strftime('%y%m%d_%H%M_logs') + '.log'
log_path = os.path.join(base_dir, 'logs', log_filename)
