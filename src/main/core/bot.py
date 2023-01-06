from __future__ import annotations

import copy
import datetime
import logging
import os
import re
from collections import Counter
from contextlib import suppress
from typing import TYPE_CHECKING, Any

import aiohttp
import discord
from discord.ext import commands, tasks
from tortoise import Tortoise
from tortoise.models import Model

from .. import __version__ as botVersion
from ..exts.meta._model import CustomCommand
from ..exts.meta._utils import getDisabledCommands
from ..exts.timer.timer import Timer, TimerData
from ..utils.cache import Cache, CacheDictProperty, CacheListProperty
from ..utils.format import formatCmdName
from ..utils.other import JSON, Blacklist, utcnow
from . import db
from .colour import ZColour
from .config import Config
from .context import Context
from .errors import CCommandDisabled, CCommandNotFound, CCommandNotInGuild
from .monkeypatch import MonkeyPatch


EXTS = []
EXTS_DIR = "exts"
EXTS_IGNORED = ("twitch.py", "youtube.py", "slash.py", "music.py")
FMT = "src/main/{}".format(EXTS_DIR)
for filename in os.listdir(FMT):
    if os.path.isdir(os.path.join(FMT, filename)):
        if filename in EXTS_IGNORED:
            continue
        if not filename.startswith("_"):
            EXTS.append("src.main.{}.{}".format(EXTS_DIR, filename))


if TYPE_CHECKING:
    from .monkeypatch import PatchedGuild


async def _callablePrefix(bot: ziBot, message: discord.Message) -> list:
    """Callable Prefix for the bot."""
    base = [bot.defPrefix]
    guild: PatchedGuild | None = message.guild  # type: ignore
    if guild:
        prefixes = await guild.getPrefixes()
        base.extend(prefixes)
    return commands.when_mentioned_or(*sorted(base))(bot, message)


class ziBot(commands.Bot):

    if TYPE_CHECKING:
        session: aiohttp.ClientSession

    def __init__(self, config: Config) -> None:
        MonkeyPatch(self).inject()
        self.config: Config = config

        # --- NOTE: Information about the bot
        self.author: str = self.config.author or "ZiRO2264#9986"
        self.version: str = f"`{botVersion}` - `overhaul`"
        self.links: dict[str, str] = self.config.links or {
            "Documentation": "https://z3r0.readthedocs.io",
            "Source Code": "https://github.com/ZiRO-Bot/ziBot",
            "Support Server": "https://discord.gg/sP9xRy6",
        }
        self.license: str = "Mozilla Public License, v. 2.0"
        # ---

        # custom intents, required since dpy v1.5
        # message content intent, required since dpy v2.0
        intents = discord.Intents.all()
        intents.message_content = True

        super().__init__(
            command_prefix=_callablePrefix,
            description=(
                "A **free and open source** multi-purpose **discord bot** " "created by ZiRO2264, formerly called `ziBot`."
            ),
            case_insensitive=True,
            intents=intents,
            heartbeat_timeout=150.0,
        )

        # make cogs case insensitive
        self._BotBase__cogs: commands.core._CaseInsensitiveDict = commands.core._CaseInsensitiveDict()

        # log
        self.logger: logging.Logger = logging.getLogger("discord")

        # Default colour for embed
        self.colour: ZColour = ZColour.me()
        self.color: ZColour = self.colour

        # Bot master(s)
        # self.master = (186713080841895936,)
        self.owner_ids: tuple = self.config.botMasters
        self.issueChannel: int = int(self.config.issueChannel or 0)

        self.blacklist: Blacklist = Blacklist("data/blacklist.json")

        self.activityIndex: int = 0
        self.commandUsage: Counter = Counter()
        self.customCommandUsage: int = 0
        # How many days before guild data get wiped when bot leaves the guild
        self.guildDelDays: int = 30

        # bot's default prefix
        self.defPrefix: str = self.config.defaultPrefix

        # News, shows up in help command
        self.news: dict[str, Any] = JSON(
            "data/news.json",
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

        @self.check
        async def _(ctx):
            """Global check"""
            if not ctx.guild:
                return True
            disableCmds = await getDisabledCommands(self, ctx.guild.id)
            cmdName = formatCmdName(ctx.command)
            if cmdName in disableCmds:
                if not ctx.author.guild_permissions.manage_guild:
                    raise commands.DisabledCommand
            return True

    async def setup_hook(self) -> None:
        """`__init__` but async"""
        if not self.owner_ids:
            # If self.master not set, warn the hoster
            self.logger.warning(
                "No master is set, you may not able to use certain commands! (Unless you own the Bot Application)"
            )

        await Tortoise.init(
            config=self.config.tortoiseConfig,
            use_tz=True,  # d.py 2.0 is tz-aware
        )
        await Tortoise.generate_schemas(safe=True)

        self.loop.create_task(self.afterReady())

    async def afterReady(self) -> None:
        """`setup_hook` but wait until ready"""
        await self.wait_until_ready()

        self.changingPresence.start()

        owner: discord.User = (await self.application_info()).owner
        if owner and owner.id not in self.owner_ids:
            self.owner_ids += (owner.id,)

        await self.manageGuildDeletion()

        for extension in EXTS:
            await self.load_extension(extension)

        if not hasattr(self, "uptime"):
            self.uptime: datetime.datetime = utcnow()

    async def getGuildConfigs(
        self,
        guildId: int,
        table: str | Model = "GuildConfigs",  # type: ignore
    ) -> dict[str, Any]:
        # TODO - Cleaner caching system, use the cache system directly to
        # handle these stuff
        if isinstance(table, str):
            table: Model | None = getattr(db, table, None)  # type: ignore

        if table is None:
            raise RuntimeError("Huh?")

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

    async def getGuildConfig(self, guildId: int, configType: str, table: str | Model = "GuildConfigs") -> Any | None:
        # Get guild's specific config
        configs: dict = await self.getGuildConfigs(guildId, table)
        return configs.get(configType)

    async def setGuildConfig(
        self, guildId: int, configType: str, configValue, table: str | Model = "GuildConfigs"
    ) -> Any | None:
        if isinstance(table, str):
            _table: Model = getattr(db, table, None)  # type: ignore
        else:
            _table: Model = table

        if not _table:
            raise RuntimeError("Wtf?")

        # Set/edit guild's specific config
        if (config := await self.getGuildConfig(guildId, configType, table)) == configValue:
            # cached value is equal to new value
            # No need to overwrite database value
            return config

        kwargs = {
            "guild_id": guildId,
            configType: configValue,
        }

        await _table.create(**kwargs)
        # await _table.update_or_create(**kwargs)

        # Overwrite current configs
        cached: CacheDictProperty = getattr(self.cache, _table._meta.db_table)
        newData = {configType: configValue}
        cached.set(guildId, newData)

        return cached.get(guildId, {}).get(configType, None)

    @tasks.loop(seconds=15)
    async def changingPresence(self) -> None:
        """A loop that change bot's status every 15 seconds."""
        await self.wait_until_ready()
        activities: tuple = (
            discord.Activity(
                name=f"over {len(self.guilds)} servers",
                type=discord.ActivityType.watching,
            ),
            discord.Activity(name=f"over {len(self.users)} users", type=discord.ActivityType.watching),
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
        timer: Timer | None = self.get_cog("Timer")  # type: ignore

        dbGuilds = await db.Guilds.all()
        dbGuilds = [i.id for i in dbGuilds]
        guildIds = [i.id for i in self.guilds]

        # Insert new guilds
        await db.Guilds.bulk_create([db.Guilds(id=i) for i in guildIds if i not in dbGuilds])

        scheduledGuilds = await db.Timer.filter(event="guild_del")
        cancelledScheduleGuilds = [await i.delete() for i in scheduledGuilds if i.owner in guildIds]
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
            timer._currentTimer.owner in cancelledScheduleGuilds or when < timer._currentTimer.expires
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
        guildId: int = timer.owner

        guildIds: list[int] = [i.id for i in self.guilds]
        if guildId in guildIds:
            # The bot rejoin, about the function
            return

        # Delete all guild's custom command
        commands = await CustomCommand.getAll(discord.Object(id=guildId))
        [await db.Commands.filter(id=i.id).delete() for i in commands]
        await db.Guilds.filter(id=guildId).delete()

        # clear guild's cache
        for dataType in self.cache.property:
            try:
                getattr(self.cache, dataType).clear(guildId)
            except KeyError:
                pass

    async def get_context(self, message, *, cls=Context):
        return await super().get_context(message, cls=cls)

    async def process_commands(self, message: discord.Message) -> (str | commands.Command | commands.Group) | None:
        # initial ctx
        ctx: Context = await self.get_context(message)

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
        if msgContent.startswith(">") or msgContent.startswith("!") or (unixStyle := msgContent.startswith("./")):
            # Also support `./` for unix-style of launching custom scripts
            priority = 1

            # Turn `>command` into `command`
            msgContent = msgContent[2 if unixStyle else 1 :]

            # Properly get command when priority is 1
            msg.content = ctx.prefix + msgContent

            # This fixes the problem, idk how ._.
            ctx = await self.get_context(msg)

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
                description=await message.guild.getFormattedPrefixes(),
                colour=ZColour.rounded(),
            )
            e.set_footer(text="Use `@{} help` to learn how to use the bot".format(me.display_name))
            await message.reply(embed=e)

        await self.process(message)

    async def on_message_edit(self, _, after):
        message = after

        # dont accept commands from bot
        if (
            message.author.bot
            or message.author.id in self.blacklist.users
            or (message.guild and message.guild.id in self.blacklist.guilds)
        ) and message.author.id not in self.owner_ids:
            return

        await self.process(message)

    async def on_app_command_completion(self, _, command: discord.app_commands.Command | discord.app_commands.ContextMenu):
        self.commandUsage[formatCmdName(command)] += 1

    async def close(self) -> None:
        """Properly close/turn off bot"""
        await super().close()
        # Close database
        await Tortoise.close_connections()
        # Close aiohttp session
        await self.session.close()

    async def run(self) -> None:

        await super().start(self.config.token, reconnect=True)
