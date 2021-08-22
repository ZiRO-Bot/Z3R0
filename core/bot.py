from __future__ import annotations

import copy
import datetime
import json
import logging
import os
import re
from collections import Counter
from contextlib import suppress
from typing import Any, Dict, Iterable, List, Optional, Union

import aiohttp
import discord
from databases import Database, DatabaseURL
from discord.ext import commands, tasks

import config
from core.colour import ZColour
from core.context import Context
from core.errors import CCommandDisabled, CCommandNotFound, CCommandNotInGuild
from core.objects import Connection
from exts.meta._utils import getDisabledCommands
from exts.meta.meta import getCustomCommands
from exts.timer.timer import Timer, TimerData
from utils import dbQuery
from utils.cache import (
    Cache,
    CacheDictProperty,
    CacheListFull,
    CacheListProperty,
    CacheUniqueViolation,
)
from utils.format import cleanifyPrefix, formatCmdName
from utils.other import Blacklist, utcnow


EXTS = []
EXTS_DIR = "exts"
EXTS_IGNORED = ("twitch.py", "youtube.py", "slash.py", "music.py")
FMT = "./{}".format(EXTS_DIR)
for filename in os.listdir(FMT):
    if os.path.isdir(os.path.join(FMT, filename)):
        if filename in EXTS_IGNORED:
            continue
        if not filename.startswith("_"):
            EXTS.append("{}.{}".format(EXTS_DIR, filename))


async def _callablePrefix(bot: ziBot, message: discord.Message) -> list:
    """Callable Prefix for the bot."""
    base = [bot.defPrefix]
    if message.guild:
        prefixes = await bot.getGuildPrefix(message.guild.id)
        base.extend(prefixes)
    return commands.when_mentioned_or(*sorted(base))(bot, message)


class ziBot(commands.Bot):

    # --- NOTE: Information about the bot
    author: str = getattr(config, "author", "ZiRO2264#9999")
    version: str = "`3.2.9` - `overhaul`"
    links: Dict[str, str] = getattr(
        config,
        "links",
        {
            "Documentation": "https://z3r0.readthedocs.io",
            "Source Code": "https://github.com/ZiRO-Bot/ziBot",
            "Support Server": "https://discord.gg/sP9xRy6",
        },
    )
    license: str = "Mozilla Public License, v. 2.0"
    # ---

    def __init__(self) -> None:
        super().__init__(
            command_prefix=_callablePrefix,
            description=(
                "A **free and open source** multi-purpose **discord bot** "
                "created by ZiRO2264, formerly called `ziBot`."
            ),
            case_insensitive=True,
            intents=discord.Intents.all(),
            heartbeat_timeout=150.0,
        )
        # make cogs case insensitive
        self._BotBase__cogs: commands.core._CaseInsensitiveDict = (
            commands.core._CaseInsensitiveDict()
        )

        # log
        self.logger: logging.Logger = logging.getLogger("discord")

        # Default colour for embed
        self.colour: ZColour = ZColour.me()
        self.color: ZColour = self.colour

        # Bot master(s)
        # self.master = (186713080841895936,)
        self.master: tuple = (
            tuple()
            if not hasattr(config, "botMasters")
            else tuple([int(master) for master in config.botMasters])
        )

        self.issueChannel: Optional[int] = (
            None if not hasattr(config, "issueChannel") else int(config.issueChannel)
        )

        self.blacklist: Blacklist = Blacklist("blacklist.json")

        self.activityIndex: int = 0
        self.commandUsage: Counter = Counter()
        self.customCommandUsage: int = 0
        # How many days before guild data get wiped when bot leaves the guild
        self.guildDelDays: int = 30

        # bot's default prefix
        self.defPrefix: str = (
            ">" if not hasattr(config, "prefix") else str(config.prefix)
        )

        # Caches
        self.cache: Cache = (
            Cache()
            .add(
                "prefixes",
                cls=CacheListProperty,
                unique=True,
                limit=15,
            )
            .add(
                "guildConfigs",
                cls=CacheDictProperty,
            )
            .add(
                "guildChannels",
                cls=CacheDictProperty,
            )
            .add(
                "guildRoles",
                cls=CacheDictProperty,
            )
            .add(
                "guildMutes",
                cls=CacheListProperty,
                unique=True,
            )
        )

        # database
        dbUrl = DatabaseURL(config.sql)
        dbKwargs = {}
        if dbUrl.scheme == "sqlite":
            # Custom factory for sqlite
            # This thing here since sqlite3 doesn't do foreign_keys=ON by
            # default
            dbKwargs = {"factory": Connection}
        self.db: Database = Database(dbUrl, **dbKwargs)

        # async init
        self.session: aiohttp.ClientSession = aiohttp.ClientSession(
            headers={"User-Agent": "Discord/Z3RO (ziBot/3.0 by ZiRO2264)"}
        )
        self.loop.create_task(self.asyncInit())
        self.loop.create_task(self.startUp())

        @self.check
        async def botCheck(ctx):
            """Global check"""
            if not ctx.guild:
                return True
            disableCmds = await getDisabledCommands(self, ctx.guild.id)
            cmdName = formatCmdName(ctx.command)
            if cmdName in disableCmds:
                if not ctx.author.guild_permissions.manage_guild:
                    raise commands.DisabledCommand
            return True

    async def asyncInit(self) -> None:
        """`__init__` but async"""
        # self.db = await aiosqlite.connect("data/database.db")
        await self.db.connect()

        async with self.db.transaction():
            # Creating all the necessary tables
            await self.db.execute(dbQuery.createGuildsTable)
            await self.db.execute(dbQuery.createGuildConfigsTable)
            await self.db.execute(dbQuery.createGuildChannelsTable)
            await self.db.execute(dbQuery.createGuildRolesTable)
            await self.db.execute(dbQuery.createPrefixesTable)
            await self.db.execute(dbQuery.createDisabledTable)
            await self.db.execute(dbQuery.createGuildMutesTable)
            await self.db.execute(dbQuery.createCaseLogTable)

    async def startUp(self) -> None:
        """Will run when the bot ready"""
        await self.wait_until_ready()
        if not self.master:
            # If self.master not set, warn the hoster
            self.logger.warning(
                "No master is set, you may not able to use certain commands! (Unless you own the Bot Application)"
            )

        # Add application owner into bot master list
        owner: discord.User = (await self.application_info()).owner
        if owner and owner.id not in self.master:
            self.master += (owner.id,)

        # change bot's presence into guild live count
        self.changing_presence.start()

        await self.manageGuildDeletion()

        if not hasattr(self, "uptime"):
            self.uptime: datetime.datetime = utcnow()

    async def getGuildConfigs(
        self, guildId: int, filters: Iterable = "*", table: str = "guildConfigs"
    ) -> Dict[str, Any]:
        # TODO: filters is deprecated, delete it later
        # Get guild configs and maybe cache it
        cached: CacheDictProperty = getattr(self.cache, table)
        if cached.get(guildId) is None:
            # Executed when guild configs is not in the cache
            row = await self.db.fetch_one(
                f"SELECT * FROM {table} WHERE guildId=:id",
                values={"id": guildId},
            )
            if row is not None:
                row = dict(row)
                row.pop("guildId", None)
                cached.set(guildId, row)
            else:
                cached.set(guildId, {})
        return cached.get(guildId, {})

    async def getGuildConfig(
        self, guildId: int, configType: str, table: str = "guildConfigs"
    ) -> Optional[Any]:
        # Get guild's specific config
        configs: dict = await self.getGuildConfigs(guildId, table=table)
        return configs.get(configType)

    async def setGuildConfig(
        self, guildId: int, configType: str, configValue, table: str = "guildConfigs"
    ) -> Optional[Any]:
        # Set/edit guild's specific config
        if (
            config := await self.getGuildConfig(guildId, configType, table)
        ) == configValue:
            # cached value is equal to new value
            # No need to overwrite database value
            return config

        async with self.db.transaction():
            await self.db.execute(
                f"""
                    INSERT INTO {table}
                        (guildId, {configType})
                    VALUES (
                        :guildId,
                        :{configType}
                    ) ON CONFLICT (guildId) DO
                    UPDATE SET
                        {configType}=:{configType}Up
                    WHERE
                        guildId=:guildIdUp
                """,
                # Doubled cuz sqlite3 uses ? (probably also affecting MySQL
                # since they use something similar, "%s").
                # while psql use $1, $2, ... which can make this code so much
                # cleaner
                values={
                    configType: configValue,
                    configType + "Up": configValue,
                    "guildId": guildId,
                    "guildIdUp": guildId,
                },
            )
            # Overwrite current configs
            cached: CacheDictProperty = getattr(self.cache, table)
            newData = {configType: configValue}
            cached.set(guildId, newData)
        return cached.get(guildId, {}).get(configType, None)

    async def getGuildPrefix(self, guildId: int) -> List[str]:
        if self.cache.prefixes.get(guildId) is None:  # type: ignore
            # Only executed when there's no cache for guild's prefix
            dbPrefixes = await self.db.fetch_all(
                "SELECT * FROM prefixes WHERE guildId=:id", values={"id": guildId}
            )

            try:
                self.cache.prefixes.extend(guildId, [p for _, p in dbPrefixes])  # type: ignore
            except ValueError:
                return []

        return self.cache.prefixes[guildId]  # type: ignore

    async def addPrefix(self, guildId: int, prefix: str) -> str:
        """Add a prefix"""
        # Fetch prefixes incase there's no cache
        await self.getGuildPrefix(guildId)

        try:
            self.cache.prefixes.add(guildId, prefix)  # type: ignore
        except CacheUniqueViolation:
            raise commands.BadArgument(
                "Prefix `{}` is already exists".format(cleanifyPrefix(self, prefix))
            )
        except CacheListFull:
            raise IndexError(
                "Custom prefixes is full! (Only allowed to add up to `{}` prefixes)".format(
                    self.cache.prefixes.limit  # type: ignore
                )
            )

        async with self.db.transaction():
            await self.db.execute(
                "INSERT INTO prefixes VALUES (:guildId, :prefix)",
                values={"guildId": guildId, "prefix": prefix},
            )

        return prefix

    async def rmPrefix(self, guildId: int, prefix: str) -> str:
        """Remove a prefix"""
        await self.getGuildPrefix(guildId)

        try:
            self.cache.prefixes.remove(guildId, prefix)  # type: ignore
        except IndexError:
            raise commands.BadArgument(
                "Prefix `{}` is not exists".format(cleanifyPrefix(self, prefix))
            )

        async with self.db.transaction():
            await self.db.execute(
                """
                    DELETE FROM prefixes
                    WHERE
                        guildId=:guildId AND prefix=:prefix
                """,
                values={"guildId": guildId, "prefix": prefix},
            )

        return prefix

    @tasks.loop(seconds=15)
    async def changing_presence(self) -> None:
        activities: tuple = (
            discord.Activity(
                name=f"over {len(self.guilds)} servers",
                type=discord.ActivityType.watching,
            ),
            discord.Activity(
                name=f"over {len(self.users)} users", type=discord.ActivityType.watching
            ),
            discord.Activity(
                name="commands | Ping me to get prefix list!",
                type=discord.ActivityType.listening,
            ),
            discord.Activity(name="bot war", type=discord.ActivityType.competing),
        )
        self.activityIndex += 1
        if self.activityIndex >= len(activities):
            self.activityIndex = 0

        await self.change_presence(activity=activities[self.activityIndex])

    async def on_ready(self) -> None:
        self.logger.warning("Ready: {0} (ID: {0.id})".format(self.user))

    async def manageGuildDeletion(self) -> None:
        """Manages guild deletion from database on boot"""
        async with self.db.transaction():
            timer: Timer = self.get_cog("Timer")

            dbGuilds = await self.db.fetch_all("SELECT id FROM guilds")
            dbGuilds = [i[0] for i in dbGuilds]
            guildIds = [i.id for i in self.guilds]

            # Insert new guilds
            guildToAdd = [{"id": i} for i in guildIds if i not in dbGuilds]
            await self.db.execute_many(
                dbQuery.insertToGuilds,
                values=guildToAdd,
            )

            # Delete deletion timer for guild where bot is in
            scheduledGuilds = await self.db.fetch_all(
                """
                    SELECT owner
                    FROM timer
                    WHERE event = "guild_del"
                """
            )
            scheduledGuilds = [i[0] for i in scheduledGuilds]
            canceledScheduleGuilds = [i for i in scheduledGuilds if i in guildIds]
            await self.db.execute_many(
                "DELETE FROM timer WHERE owner=:guildId",
                values=[{"guildId": i} for i in canceledScheduleGuilds],
            )

            # Schedule delete guild where the bot no longer in
            now = utcnow()
            when = now + datetime.timedelta(days=self.guildDelDays)
            await self.db.execute_many(
                """
                    INSERT INTO timer (event, extra, expires, created, owner)
                    VALUES ('guild_del', :extra, :expires, :created, :owner)
                """,
                values=[
                    {
                        "extra": json.dumps({"args": [], "kwargs": {}}),
                        "expires": when.timestamp(),
                        "created": now.timestamp(),
                        "owner": i,
                    }
                    for i in dbGuilds
                    if i not in guildIds and i not in scheduledGuilds
                ],
            )

            # Restart timer task
            if timer._currentTimer and (
                timer._currentTimer.owner in canceledScheduleGuilds
                or when < timer._currentTimer.expires
            ):
                timer.restartTimer()
            elif not timer._currentTimer:
                timer.restartTimer()

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Executed when bot joins a guild"""
        await self.wait_until_ready()

        async with self.db.transaction():
            return await self.db.execute(
                dbQuery.insertToGuilds, values={"id": guild.id}
            )

            # Cancel deletion
            await self.cancelDeletion(guild)

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Executed when bot leaves a guild"""
        await self.wait_until_ready()
        # Schedule deletion
        await self.scheduleDeletion(guild.id, days=self.guildDelDays)

    async def scheduleDeletion(self, guildId: int, days: int = 30) -> None:
        """Schedule guild deletion from `guilds` table"""
        timer: Timer = self.get_cog("Timer")
        now = utcnow()
        when = now + datetime.timedelta(days=days)
        await timer.createTimer(when, "guild_del", created=now, owner=guildId)

    async def cancelDeletion(self, guild: discord.Guild) -> None:
        """Cancel guild deletion"""
        timer: Timer = self.get_cog("Timer")
        # Remove the deletion timer and restart timer task
        async with self.db.transaction():
            await self.db.execute(
                """
                    DELETE FROM timer
                    WHERE
                        owner=:id AND event='guild_del'
                """,
                values={"id": guild.id},
            )
            if timer._currentTimer and timer._currentTimer.owner == guild.id:
                timer.restartTimer()

    async def on_guild_del_timer_complete(self, timer: TimerData) -> None:
        """Executed when guild deletion timer completed"""
        await self.wait_until_ready()
        guildId = timer.owner

        guildIds = [i.id for i in self.guilds]
        if guildId in guildIds:
            # The bot rejoin, about the function
            return

        async with self.db.transaction():
            # Delete all guild's custom command
            commands = await getCustomCommands(self.db, guildId)
            await self.db.execute_many(
                "DELETE FROM commands WHERE id=:id",
                values=[{"id": i.id} for i in commands],
            )

            # Delete guild from guilds table
            await self.db.execute(
                "DELETE FROM guilds WHERE id=:id", values={"id": guildId}
            )

            # clear guild's cache
            for dataType in self.cache.property:
                try:
                    getattr(self.cache, dataType).clear(guildId)
                except KeyError:
                    pass

    async def process_commands(
        self, message: discord.Message
    ) -> Optional[Union[str, commands.Command, commands.Group]]:
        # initial ctx
        ctx: Context = await self.get_context(message, cls=Context)

        if not ctx.prefix:
            return

        # 0 = Built-In, 1 = Custom
        priority = 0
        unixStyle = False

        # Handling custom command priority
        msg = copy.copy(message)
        # Get msg content without prefix
        msgContent: str = msg.content[len(ctx.prefix) :]
        # TODO: Add ability add custom priority prefix
        if (
            msgContent.startswith(">")
            or msgContent.startswith("!")
            or (unixStyle := msgContent.startswith("./"))
        ):
            # Also support `./` for unix-style of launching custom scripts
            priority = 1

            # Turn `>command` into `command`
            msgContent = msgContent[2 if unixStyle else 1 :]

            # Properly get command when priority is 1
            msg.content = ctx.prefix + msgContent

            # This fixes the problem, idk how ._.
            ctx = await self.get_context(msg, cls=Context)

        # Get arguments for custom commands
        tmp = msgContent.split(" ")
        args = (ctx, str(tmp.pop(0)).lower(), " ".join(tmp))

        # Check if user can run the command
        canRun = False
        if ctx.command:
            try:
                canRun = await ctx.command.can_run(ctx)
            except Exception:
                canRun = False

        # Apparently commands are callable, so ctx.invoke longer needed
        executeCC = self.get_command("command run")

        # Handling command invoke with priority
        if canRun:
            if priority >= 1:
                with suppress(CCommandNotFound, CCommandNotInGuild, CCommandDisabled):
                    await executeCC(*args)
                    self.customCommandUsage += 1
                    return ""
            # Since priority is 0 and it can run the built-in command,
            # no need to try getting custom command
            # Also executed when custom command failed to run
            await self.invoke(ctx)
            return ctx.command
        else:
            with suppress(CCommandNotFound, CCommandNotInGuild, CCommandDisabled):
                # Can't run built-in command, straight to trying custom command
                await executeCC(*args)
                self.customCommandUsage += 1
                return ""
            await self.invoke(ctx)
            return ctx.command

    async def formattedPrefixes(self, guildId: int) -> str:
        _prefixes = await self.getGuildPrefix(guildId)
        prefixes = []
        for pref in _prefixes:
            if pref.strip() == "`":
                prefixes.append(f"`` {pref} ``")
            elif pref.strip() == "``":
                prefixes.append(f"` {pref} `")
            else:
                prefixes.append(f"`{pref}`")
        prefixes = ", ".join(prefixes)

        result = "My default prefixes are `{}` or {}".format(
            self.defPrefix, self.user.mention
        )
        if prefixes:
            result += "\n\nCustom prefixes: {}".format(prefixes)
        return result
        # return "My prefixes are: {} or {}".format(
        #     prefixes,
        #     self.user.mention if not codeblock else ("@" + self.user.display_name),
        # )

    async def process(self, message):
        processed = await self.process_commands(message)
        if processed is not None and not isinstance(processed, str):
            self.commandUsage[formatCmdName(processed)] += 1

    async def on_message(self, message) -> None:
        # dont accept commands from bot
        if (
            message.author.bot
            or message.author.id in self.blacklist.users
            or (message.guild and message.guild.id in self.blacklist.guilds)
        ) and message.author.id not in self.master:
            return

        # if bot is mentioned without any other message, send prefix list
        pattern = f"<@(!?){self.user.id}>"
        if re.fullmatch(pattern, message.content):
            e = discord.Embed(
                description=await self.formattedPrefixes(message.guild.id),
                colour=ZColour.rounded(),
            )
            e.set_footer(
                text="Use `@{} help` to learn how to use the bot".format(
                    self.user.display_name
                )
            )
            await message.reply(embed=e)

        await self.process(message)

    async def on_message_edit(self, before, after):
        message = after

        # dont accept commands from bot
        if (
            message.author.bot
            or message.author.id in self.blacklist.users
            or (message.guild and message.guild.id in self.blacklist.guilds)
        ) and message.author.id not in self.master:
            return

        await self.process(message)

    async def close(self) -> None:
        """Properly close/turn off bot"""
        await super().close()
        # Close database
        # await self.db.close()
        await self.db.disconnect()
        # Close aiohttp session
        await self.session.close()

    def run(self) -> None:
        # load all listed extensions
        for extension in EXTS:
            self.load_extension(extension)

        super().run(config.token, reconnect=True)

    @property
    def config(self):
        return __import__("config")
