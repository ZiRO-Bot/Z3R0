import asyncio
import click
import contextlib
import core.bot as _bot
import logging

import config


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


def init_bot():
    loop = asyncio.get_event_loop()
    logger = logging.getLogger()

    bot = _bot.ziBot()
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
