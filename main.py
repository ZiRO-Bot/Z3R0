import asyncio
import click
import contextlib
import discord
import json
import logging

from core.bot import ziBot


try:
    import uvloop
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


@contextlib.contextmanager
def setup_logging():
    try:
        FORMAT = "%(asctime)s - [%(levelname)s]: %(message)s"
        DATE_FORMAT = "%d/%m/%Y (%H:%M:%S)"

        logger = logging.getLogger("discord")
        logger.setLevel(logging.INFO)

        file_handler = logging.FileHandler(
            filename="discord.log", mode="a", encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(fmt=FORMAT, datefmt=DATE_FORMAT))
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(fmt=FORMAT, datefmt=DATE_FORMAT))
        console_handler.setLevel(logging.WARNING)
        logger.addHandler(console_handler)

        yield
    finally:
        handlers = logger.handlers[:]
        for handler in handlers:
            handler.close()
            logger.removeHandler(handler)


def check_json():
    try:
        f = open("config.json", "r")
    except FileNotFoundError:
        with open("config.json", "w+") as f:
            json.dump(
                {
                    "bot_token": "",
                    "twitch": {"id": "", "secret": ""},
                    "openweather_apikey": "",
                },
                f,
                indent=4,
            )


def init_bot():
    loop = asyncio.get_event_loop()
    logger = logging.getLogger()

    check_json()

    bot = ziBot()
    bot.run()


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """Launch the bot."""
    if ctx.invoked_subcommand is None:
        loop = asyncio.get_event_loop()
        with setup_logging():
            init_bot()


if __name__ == "__main__":
    main()
