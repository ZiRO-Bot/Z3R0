import asyncio
import contextlib
import logging
import os
from logging.handlers import RotatingFileHandler

import core.bot as _bot
from utils.other import utcnow


# Use uvloop as loop policy if possible (Linux only)
try:
    import uvloop
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


def init_bot(loop):
    # jishaku env stuff
    os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
    os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"

    bot = _bot.ziBot()

    @bot.ipc.route()
    async def get_bot_stats(data):
        return {
            "users": len(bot.users),
            "guilds": len(bot.guilds),
            "commands": sum(bot.commandUsage.values()),
        }

    bot.ipc.start()
    bot.uptime = utcnow()
    bot.run()


def main():
    """Launch the bot."""
    loop = asyncio.get_event_loop()
    with setup_logging():
        init_bot(loop)


if __name__ == "__main__":
    main()
