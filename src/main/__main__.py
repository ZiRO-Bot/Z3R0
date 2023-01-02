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
        shouldRun: bool = True

        logger = logging.getLogger("discord")

        config = None
        try:
            import config as _config

            config = Config(
                _config.token,
                getattr(_config, "sql"),
                getattr(_config, "prefix"),
                getattr(_config, "botMasters"),
                getattr(_config, "issueChannel", None),
                getattr(_config, "openweather", None),
                getattr(_config, "author", None),
                getattr(_config, "links", None),
                getattr(_config, "TORTOISE_ORM", None),
            )
        except ImportError as e:
            if e.name == "config":
                logger.warn("Missing config.py, getting config from environment variables instead...")

            token = os.environ.get("ZIBOT_TOKEN")
            sql = os.environ.get("ZIBOT_DB_URL")
            if not token and not sql:
                logger.warn("Missing required environment variables, quitting...")
                shouldRun = False
            else:
                botMasters = os.environ.get("ZIBOT_BOT_MASTERS")
                config = Config(
                    token,
                    sql,
                    os.environ.get("ZIBOT_DEFAULT_PREFIX"),
                    botMasters.split(" ") if botMasters else [],
                    os.environ.get("ZIBOT_ISSUE_CHANNEL"),
                    os.environ.get("ZIBOT_OPEN_WEATHER_TOKEN"),
                    os.environ.get("ZIBOT_AUTHOR"),
                    None,  # Links a dict, idk how you'd define this in environment variables
                    None,  # Tortoise config a dict, idk how you'd define this in environment variables... well you shouldn't touch it anyway
                )

        if not shouldRun:
            exit(1)

        asyncio.run(main(config))


if __name__ == "__main__":
    run()
