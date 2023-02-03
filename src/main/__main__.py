"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import asyncio
import contextlib
import logging
import os
from logging.handlers import RotatingFileHandler

import aiohttp

from src.main.core import bot as _bot
from src.main.core.config import Config
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


async def main(config: Config):
    """Launch the bot."""
    # jishaku env stuff
    os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
    os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"

    bot = _bot.ziBot(config)
    async with aiohttp.ClientSession(headers={"User-Agent": "Discord/Z3RO (ziBot/3.0 by ZiRO2264)"}) as client:
        async with bot:
            bot.session = client
            bot.uptime = utcnow()
            await bot.run()


def run():
    with setup_logging():
        logger = logging.getLogger("discord")

        config = None
        try:
            import config as _config

            config = Config(
                _config.token,
                getattr(_config, "sql", None),
                getattr(_config, "prefix", None),
                getattr(_config, "botMasters", None),
                getattr(_config, "issueChannel", None),
                getattr(_config, "openweather", None),
                getattr(_config, "author", None),
                getattr(_config, "links", None),
                getattr(_config, "TORTOISE_ORM", None),
                getattr(_config, "internalApiHost", None),
            )
        except ImportError as e:
            if e.name == "config":
                logger.warn("Missing config.py, getting config from environment variables instead...")

            token = os.environ.get("ZIBOT_TOKEN")
            if not token:
                logger.warn("Missing required environment variables, quitting...")
            else:
                botMasters = os.environ.get("ZIBOT_BOT_MASTERS")
                config = Config(
                    token,
                    os.environ.get("ZIBOT_DB_URL"),
                    os.environ.get("ZIBOT_DEFAULT_PREFIX"),
                    botMasters.split(" ") if botMasters else [],
                    os.environ.get("ZIBOT_ISSUE_CHANNEL"),
                    os.environ.get("ZIBOT_OPEN_WEATHER_TOKEN"),
                    os.environ.get("ZIBOT_AUTHOR"),
                    None,  # Links a dict, idk how you'd define this in environment variables
                    None,  # Tortoise config a dict, idk how you'd define this in environment variables... well you shouldn't touch it anyway
                    os.environ.get("ZIBOT_INTERNAL_API_HOST"),
                )

        if not config:
            exit(1)

        asyncio.run(main(config))


if __name__ == "__main__":
    run()
