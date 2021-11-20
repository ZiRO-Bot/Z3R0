from __future__ import annotations

import copy
import datetime
import logging
import os
import re
import warnings
from collections import Counter
from contextlib import suppress
from typing import Any, Dict, Iterable, List, Optional, Union

import aiohttp
import discord
from discord.ext import commands, tasks
from tortoise import Tortoise
from tortoise.models import Model

import config
from core import db
from core.colour import ZColour
from core.context import Context
from core.errors import CCommandDisabled, CCommandNotFound, CCommandNotInGuild
from exts.meta._custom_command import getCustomCommands
from exts.meta._utils import getDisabledCommands
from exts.timer.timer import Timer, TimerData
from utils.cache import (
    Cache,
    CacheDictProperty,
    CacheListFull,
    CacheListProperty,
    CacheUniqueViolation,
)
from utils.format import cleanifyPrefix, formatCmdName
from utils.other import JSON, Blacklist, utcnow


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
    version: str = "`3.4.4` - `overhaul`"
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
        # custom intents, required since dpy v1.5
        intents = discord.Intents.all()

        super().__init__(
            command_prefix=_callablePrefix,
            description=(
                "A **free and open source** multi-purpose **discord bot** "
                "created by ZiRO2264, formerly called `ziBot`."
            ),
            case_insensitive=True,
            intents=intents,
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
        self.owner_ids: tuple = (
            tuple()
            if not hasattr(config, "botMasters")
            else tuple([int(master) for master in config.botMasters])
        )

        self.issueChannel: int = getattr(config, "issueChannel", 0)

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

        # News, shows up in help command
        self.news: Dict[str, Any] = JSON(
            "news.json",
            {
                "time": 0,
                "content": "Nothing to see here...",
            },
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
        await Tortoise.init(
            config=config.TORTOISE_ORM,
            # db_url=config.sql,
            # modules={"models": ["core.db"]},
            use_tz=True,  # d.py now tz-aware
        )
        await Tortoise.generate_schemas(safe=True)

    # @property
    # def db(self) -> BaseDBAsyncClient:  # noqa: F811 - Unrelated
    #     return Tortoise.get_connection("default")

    async def startUp(self) -> None:
        """Will run when the bot ready"""
        await self.wait_until_ready()

        if not self.owner_ids:
            # If self.master not set, warn the hoster
            self.logger.warning(
                "No master is set, you may not able to use certain commands! (Unless you own the Bot Application)"
            )

        # Add application owner into owner_ids list
        owner: discord.User = (await self.application_info()).owner
        if owner and owner.id not in self.owner_ids:
            self.owner_ids += (owner.id,)

        # change bot's presence into guild live count
        self.changingPresence.start()

        await self.manageGuildDeletion()

        if not hasattr(self, "uptime"):
            self.uptime: datetime.datetime = utcnow()

    @property
    def master(self):
        warnings.warn("Bot.master is deprecated, use self.owner_ids instead")
        return self.owner_ids

    async def getGuildConfigs(
        self,
        guildId: int,
        filters: Iterable = "*",
        table: Union[str, Model] = "GuildConfigs",  # type: ignore
    ) -> Dict[str, Any]:
        if isinstance(table, str):
            table: Optional[Model] = getattr(db, table, None)  # type: ignore

        if table is None:
            raise RuntimeError("Huh?")

        # TODO: filters is deprecated, delete it later
        # Get guild configs and maybe cache it
        cached: CacheDictProperty = getattr(self.cache, table._meta.db_table)
        if cached.get(guildId) is None:
            # Executed when guild configs is not in the cache
            config = await table.filter(guild_id=guildId).values()

            if config:
                row = config[0]
                for i in ("id", "guild_id"):
                    row.pop(i, None)
                cached.set(guildId, row)
            else:
                cached.set(guildId, {})
        return cached.get(guildId, {})

    async def getGuildConfig(
        self, guildId: int, configType: str, table: Union[str, Model] = "GuildConfigs"
    ) -> Optional[Any]:
        # Get guild's specific config
        configs: dict = await self.getGuildConfigs(guildId, table=table)
        return configs.get(configType)

    async def setGuildConfig(
        self, guildId: int, configType: str, configValue, table: Union[str, Model] = "GuildConfigs"  # type: ignore
    ) -> Optional[Any]:
        if isinstance(table, str):
            table: Model = getattr(db, table, None)  # type: ignore

        if not table:
            raise RuntimeError("Wtf?")

        # Set/edit guild's specific config
        if (
            config := await self.getGuildConfig(guildId, configType, table)
        ) == configValue:
            # cached value is equal to new value
            # No need to overwrite database value
            return config

        kwargs = {
            "guild_id": guildId,
            configType: configValue,
        }

        await table.create(**kwargs)
        # await table.update_or_create(**kwargs)

        # Overwrite current configs
        cached: CacheDictProperty = getattr(self.cache, table._meta.db_table)
        newData = {configType: configValue}
        cached.set(guildId, newData)

        return cached.get(guildId, {}).get(configType, None)

    async def getGuildPrefix(self, guildId: int) -> List[str]:
        if self.cache.prefixes.get(guildId) is None:  # type: ignore
            # Only executed when there's no cache for guild's prefix
            dbPrefixes = await db.Prefixes.filter(guild_id=guildId)

            try:
                self.cache.prefixes.extend(guildId, [p.prefix for p in dbPrefixes])  # type: ignore
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

        await db.Prefixes.create(prefix=prefix, guild_id=guildId)

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

        [
            await i.delete()
            for i in await db.Prefixes.filter(prefix=prefix, guild_id=guildId)
        ]

        return prefix

    @tasks.loop(seconds=15)
    async def changingPresence(self) -> None:
        """A loop that change bot's status every 15 seconds."""
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
        timer: Optional[Timer] = self.get_cog("Timer")  # type: ignore

        dbGuilds = await db.Guilds.all()
        dbGuilds = [i.id for i in dbGuilds]
        guildIds = [i.id for i in self.guilds]

        # Insert new guilds
        await db.Guilds.bulk_create(
            [db.Guilds(id=i) for i in guildIds if i not in dbGuilds]
        )

        scheduledGuilds = await db.Timer.filter(event="guild_del")
        cancelledScheduleGuilds = [
            await i.delete() for i in scheduledGuilds if i.owner in guildIds
        ]
        scheduledGuildIds = [i.id for i in scheduledGuilds]

        # Schedule delete guild where the bot no longer in
        now = utcnow()
        when = now + datetime.timedelta(days=self.guildDelDays)

        await db.Timer.bulk_create(
            [
                db.Timer(
                    id=i,
                    event="guild_del",
                    extra={"args": [], "kwargs": {}},
                    expires=when,
                    created=now,
                    owner=i,
                )
                for i in dbGuilds
                if i not in guildIds and i not in scheduledGuildIds
            ]
        )

        if not timer:
            return

        # Restart timer task
        if timer._currentTimer and (
            timer._currentTimer.owner in cancelledScheduleGuilds
            or when < timer._currentTimer.expires
        ):
            timer.restartTimer()
        elif not timer._currentTimer:
            timer.restartTimer()

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Executed when bot joins a guild"""
        await self.wait_until_ready()

        await db.Guilds.create(id=guild.id)

        # Cancel deletion
        await self.cancelDeletion(guild)

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Executed when bot leaves a guild"""
        await self.wait_until_ready()
        # Schedule deletion
        await self.scheduleDeletion(guild.id, days=self.guildDelDays)

    async def scheduleDeletion(self, guildId: int, days: int = 30) -> None:
        """Schedule guild deletion from `guilds` table"""
        timer: Timer = self.get_cog("Timer")  # type: ignore
        now = utcnow()
        when = now + datetime.timedelta(days=days)
        await timer.createTimer(when, "guild_del", created=now, owner=guildId)

    async def cancelDeletion(self, guild: discord.Guild) -> None:
        """Cancel guild deletion"""
        timer: Timer = self.get_cog("Timer")  # type: ignore

        # Remove the deletion timer and restart timer task
        await db.Timer.filter(owner=guild.id, event="guild_del").delete()

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

        # Delete all guild's custom command
        commands = await getCustomCommands(guildId)
        [await db.Commands.filter(id=i.id).delete() for i in commands]
        await db.Guilds.filter(id=guildId).delete()

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
        if (not canRun or priority >= 1) and executeCC:
            with suppress(CCommandNotFound, CCommandNotInGuild, CCommandDisabled):
                await executeCC(*args)  # type: ignore
                self.customCommandUsage += 1
                return ""
        # Since priority is 0 and it can run the built-in command,
        # no need to try getting custom command
        # Also executed when custom command failed to run
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
            self.defPrefix, self.user.mention  # type: ignore
        )
        if prefixes:
            result += "\n\nCustom prefixes: {}".format(prefixes)
        return result

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
        ) and message.author.id not in self.owner_ids:
            return

        me: discord.ClientUser = self.user  # type: ignore

        # if bot is mentioned without any other message, send prefix list
        pattern = f"<@(!?){me.id}>"
        if re.fullmatch(pattern, message.content):
            e = discord.Embed(
                description=await self.formattedPrefixes(message.guild.id),
                colour=ZColour.rounded(),
            )
            e.set_footer(
                text="Use `@{} help` to learn how to use the bot".format(
                    me.display_name
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
        ) and message.author.id not in self.owner_ids:
            return

        await self.process(message)

    async def close(self) -> None:
        """Properly close/turn off bot"""
        await super().close()
        # Close database
        await Tortoise.close_connections()
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
