import os
import json

from aiogram.types import BotCommand

from configs import BASE_DIR


# Open json file and read commands
with open(os.path.join(BASE_DIR, 'bot', 'static', 'commands.json'), 'r') as commands_file:
    commands_dict = json.load(commands_file)


# List of commands applied to all languages
def en_commands_list() -> list[BotCommand]:
    commands_en = []
    for command_text, description_dict in commands_dict.items():
        command = BotCommand(command=command_text, description=description_dict['en'])
        commands_en.append(command)
    return commands_en


# List of commands applied to russian language
def ru_commands_list() -> list[BotCommand]:
    commands_ru = []
    for command_text, description_dict in commands_dict.items():
        command = BotCommand(command=command_text, description=description_dict['ru'])
        commands_ru.append(command)
    return commands_ru
