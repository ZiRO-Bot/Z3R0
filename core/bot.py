import aiohttp
import copy
import datetime
import discord
import json
import os
import logging
import re
import uuid


from core.context import Context
from core.errors import CCommandNotFound, CCommandNotInGuild, CCommandDisabled
from core.objects import Connection
from exts.meta import getCustomCommands
from exts.timer import TimerData, Timer
from exts.utils import dbQuery
from exts.utils.cache import (
    Cache,
    CacheListProperty,
    CacheUniqueViolation,
    CacheListFull,
    CacheDictProperty,
)
from exts.utils.format import cleanifyPrefix
from exts.utils.other import Blacklist, utcnow
from databases import Database
from discord.ext import commands, tasks
from typing import Union, Iterable


import config


EXTS = []
EXTS_DIR = "exts"
EXTS_IGNORED = ("twitch.py", "youtube.py", "slash.py", "music.py")
for filename in os.listdir("./{}".format(EXTS_DIR)):
    if filename in EXTS_IGNORED:
        continue
    if filename.endswith(".py"):
        EXTS.append("{}.{}".format(EXTS_DIR, filename[:-3]))


async def _callablePrefix(bot, message):
    """Callable Prefix for the bot."""
    base = [bot.defPrefix]
    if message.guild:
        prefixes = await bot.getGuildPrefix(message.guild.id)
        base.extend(prefixes)
    return commands.when_mentioned_or(*sorted(base))(bot, message)


class ziBot(commands.Bot):

    # --- NOTE: Information about the bot
    author = "ZiRO2264#4572"
    version = "`3.0.0` - `overhaul`"
    links = {
        "Documentation (Coming Soon\u2122)": "",
        "Source Code": "https://github.com/ZiRO-Bot/ziBot",
        "Support Server": "https://discord.gg/sP9xRy6",
    }
    license = "Mozilla Public License, v. 2.0"
    # ---

    def __init__(self):
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
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()

        # log
        self.logger = logging.getLogger("discord")

        # Default colour for embed
        self.colour = discord.Colour(0x3DB4FF)
        self.color = self.colour

        # Bot master(s)
        # self.master = (186713080841895936,)
        self.master = (
            tuple()
            if not hasattr(config, "botMasters")
            else tuple([int(master) for master in config.botMasters])
        )

        self.issueChannel = (
            None if not hasattr(config, "issueChannel") else int(config.issueChannel)
        )

        self.blacklist = Blacklist("blacklist.json")

        self.activityIndex = 0
        self.commandUsage = 0
        self.customCommandUsage = 0
        # How many days before guild data get wiped when bot leaves the guild
        self.guildDelDays = 30

        # bot's default prefix
        self.defPrefix = ">" if not hasattr(config, "prefix") else config.prefix

        # Caches
        self.cache = (
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
        )

        # database
        self.db = Database(config.sql, factory=Connection)

        # async init
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": "Discord/Z3RO (ziBot/3.0 by ZiRO2264)"}
        )
        self.loop.create_task(self.asyncInit())
        self.loop.create_task(self.startUp())

    async def asyncInit(self):
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

    async def startUp(self):
        """Will run when the bot ready"""
        await self.wait_until_ready()
        if not self.master:
            # If self.master not set, warn the hoster
            self.logger.warning(
                "No master is set, you may not able to use certain commands! (Unless you own the Bot Application)"
            )
        # Add application owner into bot master list
        owner = (await self.application_info()).owner
        if owner and owner.id not in self.master:
            self.master += (owner.id,)

        # change bot's presence into guild live count
        self.changing_presence.start()

        await self.manageGuildDeletion()

        if not hasattr(self, "uptime"):
            self.uptime = utcnow()

    async def getGuildConfigs(
        self, guildId: int, filters: Iterable = "*", table: str = "guildConfigs"
    ):
        # Get guild configs and maybe cache it
        cached: CacheDictProperty = getattr(self.cache, table)
        if cached.get(guildId) is None or not [
            i for i in cached.get(guildId, {}).keys() if i in filters
        ]:
            # Executed when guild configs is not in the cache
            row = await self.db.fetch_one(
                f"SELECT {', '.join(filters)} FROM {table} WHERE guildId=:id",
                values={"id": guildId},
            )
            if row:
                row = dict(row)
                row.pop("guildId", None)
                cached.set(guildId, row)
                return row
        return cached[guildId]

    async def getGuildConfig(
        self, guildId: int, configType: str, table: str = "guildConfigs"
    ):
        # Get guild's specific config
        configs: dict = await self.getGuildConfigs(guildId, (configType,), table)
        return configs.get(configType)

    async def setGuildConfig(
        self, guildId: int, configType: str, configValue, table: str = "guildConfigs"
    ):
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

    async def getGuildPrefix(self, guildId):
        if self.cache.prefixes.get(guildId) is None:
            # Only executed when there's no cache for guild's prefix
            dbPrefixes = await self.db.fetch_all(
                "SELECT * FROM prefixes WHERE guildId=:id", values={"id": guildId}
            )

            try:
                self.cache.prefixes.extend(guildId, [p for _, p in dbPrefixes])
            except ValueError:
                return []

        return self.cache.prefixes[guildId]

    async def addPrefix(self, guildId, prefix):
        """Add a prefix"""
        # Fetch prefixes incase there's no cache
        await self.getGuildPrefix(guildId)

        try:
            self.cache.prefixes.add(guildId, prefix)
        except CacheUniqueViolation:
            raise commands.BadArgument(
                "Prefix `{}` is already exists".format(cleanifyPrefix(self, prefix))
            )
        except CacheListFull:
            raise IndexError(
                "Custom prefixes is full! (Only allowed to add up to `{}` prefixes)".format(
                    self.cache.prefixes.limit
                )
            )

        async with self.db.transaction():
            await self.db.execute(
                "INSERT INTO prefixes VALUES (:guildId, :prefix)",
                values={"guildId": guildId, "prefix": prefix},
            )

        return prefix

    async def rmPrefix(self, guildId, prefix):
        """Remove a prefix"""
        await self.getGuildPrefix(guildId)

        try:
            self.cache.prefixes.remove(guildId, prefix)
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
    async def changing_presence(self):
        activities = (
            discord.Activity(
                name=f"over {len(self.guilds)} servers",
                type=discord.ActivityType.watching,
            ),
            discord.Activity(
                name=f"over {len(self.users)} users", type=discord.ActivityType.watching
            ),
            discord.Activity(
                name=f"commands | Ping me to get prefix list!",
                type=discord.ActivityType.listening,
            ),
            discord.Activity(name=f"bot war", type=discord.ActivityType.competing),
        )
        try:
            self.activityIndex += 1
            activity = activities[self.activityIndex]
        except IndexError:
            self.activityIndex = 0
            activity = activities[self.activityIndex]

        await self.change_presence(activity=activities[self.activityIndex])

    async def on_ready(self):
        self.logger.warning("Ready: {0} (ID: {0.id})".format(self.user))

    async def manageGuildDeletion(self):
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
            if timer.currentTimer and (
                timer.currentTimer.owner in canceledScheduleGuilds
                or when < timer.currentTimer.expires
            ):
                timer.restartTimer()
            elif not timer.currentTimer:
                timer.restartTimer()

    async def on_guild_join(self, guild):
        """Executed when bot joins a guild"""
        await self.wait_until_ready()

        async with self.db.transaction():
            return await self.db.execute(
                dbQuery.insertToGuilds, values={"id": guild.id}
            )

            # Cancel deletion
            await self.cancelDeletion(guild)

    async def on_guild_remove(self, guild):
        """Executed when bot leaves a guild"""
        await self.wait_until_ready()
        # Schedule deletion
        await self.scheduleDeletion(guild.id, days=self.guildDelDays)

    async def scheduleDeletion(self, guildId: int, days: int = 30):
        """Schedule guild deletion from `guilds` table"""
        timer: Timer = self.get_cog("Timer")
        now = utcnow()
        when = now + datetime.timedelta(days=days)
        await timer.createTimer(when, "guild_del", created=now, owner=guildId)

    async def cancelDeletion(self, guild: discord.Guild):
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
            if timer.currentTimer and timer.currentTimer.owner == guild.id:
                timer.restartTimer()

    async def on_guild_del_timer_complete(self, timer: TimerData):
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

            for dataType in ("prefixes", "guildConfigs", "disabled"):
                try:
                    getattr(self.cache, dataType).clear(guildId)
                except KeyError:
                    pass

    async def process_commands(self, message):
        # initial ctx
        ctx = await self.get_context(message, cls=Context)

        if not ctx.prefix:
            return

        # 0 = Built-In, 1 = Custom
        priority = 0
        unixStyle = False

        # Handling custom command priority
        msg = copy.copy(message)
        # Get msg content without prefix
        msgContent: str = msg.content[len(ctx.prefix) :]
        if msgContent.startswith(">") or (unixStyle := msgContent.startswith("./")):
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
        args = (ctx, tmp.pop(0), " ".join(tmp))

        # Check if user can run the command
        canRun = False
        if ctx.command:
            try:
                canRun = await ctx.command.can_run(ctx)
            except commands.CheckFailure:
                canRun = False

        # Apparently commands are callable, so ctx.invoke longer needed
        executeCC = self.get_command("command run")
        # Handling command invoke with priority
        if canRun:
            if priority >= 1:
                try:
                    await executeCC(*args)
                    self.customCommandUsage += 1
                    return
                except (CCommandNotFound, CCommandNotInGuild, CCommandDisabled):
                    # Failed to run custom command, revert to built-in command
                    return await self.invoke(ctx)
            # Since priority is 0 and it can run the built-in command,
            # no need to try getting custom command
            return await self.invoke(ctx)
        else:
            # Can't run built-in command, straight to trying custom command
            await executeCC(*args)
            self.customCommandUsage += 1
            return

    async def formattedPrefixes(self, guildId):
        prefixes = await self.getGuildPrefix(guildId)
        prefixes = ", ".join([f"`{x}`" for x in prefixes])
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

    async def on_message(self, message):
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
                colour=discord.Colour.rounded(),
            )
            e.set_footer(
                text="Use `@{} help` to learn how to use the bot".format(
                    self.user.display_name
                )
            )
            await message.reply(embed=e)

        processed = await self.process_commands(message)
        if not processed:
            self.commandUsage += 1

    async def close(self):
        """Properly close/turn off bot"""
        await super().close()
        # Close database
        # await self.db.close()
        await self.db.disconnect()
        # Close aiohttp session
        await self.session.close()

    def run(self):
        # load all listed extensions
        for extension in EXTS:
            self.load_extension(extension)

        super().run(config.token, reconnect=True)

    @property
    def config(self):
        return __import__("config")
