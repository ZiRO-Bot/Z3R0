import asyncio
import json
import logging

from bot import ziBot

def check_jsons():
    try:
        f = open('config.json', 'r')
    except FileNotFoundError:
        token = input('Enter your bot\'s token: ')
        with open('config.json', 'w+') as f:
            json.dump({"token": token}, f, indent=4)


def setup_logging():
    FORMAT = '%(asctime)s - [%(levelname)s]: %(message)s'
    DATE_FORMAT = '%d/%m/%Y (%H:%M:%S)'

    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(filename='discord.log',
            mode='a',
            encoding='utf-8')
    file_handler.setFormatter(
            logging.Formatter(fmt=FORMAT, datefmt=DATE_FORMAT))
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
            logging.Formatter(fmt=FORMAT, datefmt=DATE_FORMAT))
    console_handler.setLevel(logging.WARNING)
    logger.addHandler(console_handler)

def init_bot():
    bot = ziBot()
    with open('config.json', 'r') as f:
        data=json.load(f)
    bot.remove_command('help')
    bot.run()

if __name__ == "__main__":
    check_jsons()
    setup_logging()
    init_bot()