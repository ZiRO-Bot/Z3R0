import asyncio
import contextlib
import logging
import os
from logging.handlers import RotatingFileHandler

import aiohttp

from src.main.core import bot as _bot
from src.main.utils.other import utcnow


# Use uvloop as loop policy if possible (Linux only)
try:
    import uvloop  # type: ignore - error is handled
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# Create data directory if its not exist
try:
    os.makedirs("data")
except FileExistsError:
    pass


@contextlib.contextmanager
def setup_logging():
    try:
        FORMAT = "[%(asctime)s] [%(levelname)s]: %(message)s"
        DATE_FORMAT = "%d/%m/%Y (%H:%M:%S)"

        logger = logging.getLogger("discord")
        logger.setLevel(logging.INFO)

        file_handler = RotatingFileHandler(
            filename="discord.log",
            mode="a",
            encoding="utf-8",
            maxBytes=33554432,
            backupCount=5,
        )  # maxBytes = 33554432 -> 32 mb
        file_handler.setFormatter(logging.Formatter(fmt=FORMAT, datefmt=DATE_FORMAT))
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(fmt=FORMAT, datefmt=DATE_FORMAT))
        console_handler.setLevel(logging.WARNING)
        logger.addHandler(console_handler)

        yield
    finally:
        handlers = logger.handlers[:]  # type: ignore
        for handler in handlers:
            handler.close()
            logger.removeHandler(handler)  # type: ignore


async def main():
    """Launch the bot."""
    # jishaku env stuff
    os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
    os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"

    bot = _bot.ziBot()
    async with aiohttp.ClientSession(headers={"User-Agent": "Discord/Z3RO (ziBot/3.0 by ZiRO2264)"}) as client:
        async with bot:
            bot.session = client
            bot.uptime = utcnow()
            await bot.run()


def run():
    with setup_logging():
        asyncio.run(main())


if __name__ == "__main__":
    run()
