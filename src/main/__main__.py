"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import argparse
import asyncio
import contextlib
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import aiohttp
from tortoise import Tortoise, connection

from src.main.core import bot as _bot
from src.main.core import db
from src.main.core.config import Config
from src.main.utils.other import utcnow


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


async def _run(config: Config):
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
                getattr(_config, "test", False),
                getattr(_config, "zmqPorts", None),
                None,
                False,
            )
        except ImportError as e:
            if e.name == "config":
                logger.warn("Missing config.py, getting config from environment variables instead...")

            token = os.environ.get("ZIBOT_TOKEN")
            if not token:
                logger.warn("Missing required environment variables, quitting...")
            else:
                botMasters = os.environ.get("ZIBOT_BOT_MASTERS")
                PUB = int(os.environ.get("ZIBOT_ZMQ_PUB", 0))
                SUB = int(os.environ.get("ZIBOT_ZMQ_SUB", 0))
                REP = int(os.environ.get("ZIBOT_ZMQ_REP", 0))
                zmqPorts = None
                if not all([i <= 0 for i in (PUB, SUB, REP)]):
                    zmqPorts = {
                        "PUB": PUB,
                        "SUB": SUB,
                        "REP": REP,
                    }

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
                    False,  # Can't test inside docker
                    zmqPorts,
                    None,
                    False,
                )

        if not config:
            exit(1)

        # Use uvloop as loop policy if possible (Linux only)
        try:
            import uvloop  # type: ignore - error is handled
        except ImportError:
            asyncio.run(_run(config))
        else:
            if sys.version_info >= (3, 11):
                with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
                    runner.run(_run(config))
            else:
                uvloop.install()
                asyncio.run(_run(config))


async def _datamigration(config: Config):
    """|coro|

    The actual data migration. Should only be ran once, running it again may
    cause some issue.

    Usage
    -----
    %> poetry run datamigration --dest "postgres://user:pass@host:port/db" --source "sqlite:///data/database.db"
    %> poetry run datamigration --dest "mysql://user@host/db" --source "sqlite:///database.db"
    """
    logger = logging.getLogger("discord")
    await Tortoise.init(config=config.tortoiseConfig)
    logger.warn("Trying to generate scheme...")
    await Tortoise.generate_schemas(True)

    models = [
        db.Guilds,
        db.Timer,
        db.Commands,
        db.CommandsLookup,
        db.Disabled,
        db.Prefixes,
        db.GuildConfigs,
        db.GuildChannels,
        db.GuildRoles,
        db.GuildMutes,
        db.CaseLog,
    ]
    for index, model in enumerate(models):
        current = await model.all(using_db=Tortoise.get_connection("default"))

        if model is db.Commands:
            newList = []
            for data in current:
                # Internal API, as far as I know this is the only way to force TortoiseORM to NOT generate new ID
                data._custom_generated_pk = True
                newList.append(data)
            current = newList
        logger.warn(f"Migrating {model.__name__} [{index + 1}/{len(models)}]...")
        await model.bulk_create(current, ignore_conflicts=True, using_db=Tortoise.get_connection("dest"))

    logger.warning("Data has been migrated!")
    return await connection.connections.close_all()


def datamigration():
    """
    Config and Args handler before actually doing the data migration
    """
    source = None
    try:
        import config

        source = config.sql
    except:
        pass

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--source", default=source)
    parser.add_argument("--dest", required=True)
    parsed = parser.parse_args(sys.argv[1:])

    config = Config(
        "",
        databaseUrl=parsed.source,
        destUrl=parsed.dest,
        isDataMigration=True,
    )

    with setup_logging():
        asyncio.run(_datamigration(config))


def main():
    """
    CLI Command Handler

    Will run the bot by default if no command is specified
    """
    command = None
    try:
        command = sys.argv[1]
    except IndexError:
        pass

    if command:
        if command == "datamigration":
            return datamigration()
    # Since no valid command is detected we fallback to running the bot
    return run()


if __name__ == "__main__":
    main()
