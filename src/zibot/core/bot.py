"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import asyncio
import copy
import datetime
import json
import logging
import os
import re
import shutil
import sys
from collections import Counter
from contextlib import suppress
from typing import TYPE_CHECKING, Any

import aiohttp
import discord
import zmq
import zmq.asyncio
from aerich import Command as AerichCommand
from discord.ext import commands, tasks
from discord.ui import Button
from tortoise import Tortoise, connections
from tortoise.exceptions import DBConnectionError, OperationalError
from tortoise.models import Model

from .. import __version__ as botVersion
from ..exts.meta._custom_command import CustomCommand
from ..exts.meta._errors import CCommandDisabled, CCommandNotFound, CCommandNotInGuild
from ..exts.meta._utils import getDisabledCommands
from ..exts.timer.timer import Timer, TimerData
from ..utils import utcnow
from ..utils.format import formatCmdName
from . import db
from .colour import ZColour
from .config import Config
from .context import Context
from .data import JSON, Blacklist, Cache, CacheDictProperty, CacheListProperty
from .guild import GuildWrapper
from .i18n import FluentTranslator, Localization


EXTS = []
EXTS_DIR = "exts"
EXTS_IGNORED = ("twitch.py", "youtube.py", "slash.py", "music.py")
FMT = "src/zibot/{}".format(EXTS_DIR)
for filename in os.listdir(FMT):
    if os.path.isdir(os.path.join(FMT, filename)):
        if filename in EXTS_IGNORED:
            continue
        if not filename.startswith("_"):
            EXTS.append("zibot.{}.{}".format(EXTS_DIR, filename))


EMOJI_REGEX = re.compile(r";(?P<name>[a-zA-Z0-9_]{2,32});")


async def _callablePrefix(bot: ziBot, message: discord.Message) -> list:
    """Callable Prefix for the bot."""
    base = [bot.defPrefix]
    guild: GuildWrapper | None = GuildWrapper.fromContext(message.guild, bot)
    if guild:
        prefixes = await guild.getPrefixes()
        base.extend(prefixes)
    return commands.when_mentioned_or(*sorted(base))(bot, message)


__all__ = ("ziBot",)


class ziBot(commands.Bot):
    if TYPE_CHECKING:
        session: aiohttp.ClientSession
        i18n: Localization

    def __init__(self, config: Config) -> None:
        self.monkeyPatch()

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
        intents = discord.Intents.all()
        # message content intent, required since dpy v2.0
        intents.message_content = True

        super().__init__(
            command_prefix=_callablePrefix,
            description="bot-description",
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
        # TODO: Improve type checking support
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

        self.pubSocket: zmq.asyncio.Socket | None = None
        self.subSocket: zmq.asyncio.Socket | None = None
        self.repSocket: zmq.asyncio.Socket | None = None
        self.socketTasks: list[asyncio.Task] = []

        self.exitCode: int = 0

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

    @property
    def ownerIds(self):
        return self.owner_ids

    @ownerIds.setter
    def ownerIds(self, newIds):
        self.owner_ids = newIds

    def monkeyPatch(self):
        oldInit = Button.__init__

        def newInit(*args, **kwargs):
            """
            MonkeyPatch to make Enum values work in Buttons
            """
            emoji = kwargs.pop("emoji", None)
            if emoji.__class__.__name__.startswith("_EnumValue"):
                emoji = str(emoji)
            kwargs["emoji"] = emoji
            oldInit(*args, **kwargs)

        Button.__init__ = newInit  # type: ignore

    async def setup_hook(self) -> None:
        """`__init__` but async"""
        if not self.ownerIds:
            # If self.master not set, warn the hoster
            self.logger.warning(
                "No master is set, you may not able to use certain commands! (Unless you own the Bot Application)"
            )

        if self.config.test:
            await Tortoise.init(
                config=self.config.tortoiseConfig,
                use_tz=True,  # d.py 2.0 is tz-aware
            )
            with suppress(DBConnectionError, OperationalError):
                await Tortoise._drop_databases()

        self.i18n = await Localization.init()
        await self.tree.set_translator(FluentTranslator(self))

        migrationDir = self.config.migrationDir

        aerichCmd = AerichCommand(
            tortoise_config=self.config.tortoiseConfig,
            location=str(migrationDir),
        )

        if migrationDir.exists():
            await aerichCmd.init()

            try:
                update = await aerichCmd.migrate()

                if update:
                    upgrades = await aerichCmd.upgrade()
                    if len(upgrades) > 0:
                        self.logger.warning(f"DB Upgrades done ({len(upgrades)}): {', '.join(upgrades)}")

            except AttributeError:
                self.logger.warning(
                    "Unable to retrieve model history from the database! " "Creating model history from scratch..."
                )

                self._cleanMigrationDir()

                await aerichCmd.init_db(True)
        else:
            await aerichCmd.init_db(True)

        await Tortoise.generate_schemas(safe=True)

        self.loop.create_task(self.afterReady())

    def _cleanMigrationDir(self):
        directory = self.config.migrationDir
        for filename in os.listdir(directory):
            filePath = directory / filename
            try:
                if os.path.isfile(filePath) or os.path.islink(filePath):
                    os.unlink(filePath)
                elif os.path.isdir(filePath):
                    shutil.rmtree(filePath)
            except Exception as err:
                print(f"Failed to delete {filePath}. Reason: {err}")

    async def afterReady(self) -> None:
        """`setup_hook` but wait until ready"""
        if not self.config.test:
            await self.waitUntilReady()

            owner: discord.User = (await self.application_info()).owner
            if owner and owner.id not in self.ownerIds:
                self.ownerIds += (owner.id,)

            await self.manageGuildDeletion()

            self.changingPresence.start()
            await self.zmqBind()

        for extension in EXTS:
            await self.load_extension(extension)

        for command in self.commands:
            if merge := getattr(command, "__merge_group__", None):
                self.tree.get_command(merge.name).add_command(command.app_command)  # type: ignore
                self.tree.remove_command(command.name)

        if not hasattr(self, "uptime"):
            self.uptime: datetime.datetime = utcnow()

    async def on_ready(self) -> None:
        self.logger.warning("Ready: {0} (ID: {0.id})".format(self.user))

    async def zmqBind(self):
        pubPort = self.config.zmqPorts.get("PUB")
        subPort = self.config.zmqPorts.get("SUB")
        repPort = self.config.zmqPorts.get("REP")

        if not pubPort and not subPort and not repPort:
            return

        context = zmq.asyncio.Context.instance()

        if pubPort:
            self.pubSocket = context.socket(zmq.PUB)
            self.pubSocket.bind(f"tcp://*:{pubPort}")

        if subPort:
            self.subSocket = context.socket(zmq.SUB)
            self.subSocket.setsockopt(zmq.SUBSCRIBE, b"")
            self.subSocket.bind(f"tcp://*:{subPort}")
            self.socketTasks.append(asyncio.create_task(self.onZMQReceivePUBMessage()))

        if repPort:
            self.repSocket = context.socket(zmq.REP)
            self.repSocket.bind(f"tcp://*:{repPort}")
            self.socketTasks.append(asyncio.create_task(self.onZMQReceiveREQMessage()))

    async def onZMQReceivePUBMessage(self):
        if not self.subSocket:
            return

        try:
            while True:
                message = json.loads(await self.subSocket.recv_string())

                channel: discord.TextChannel = self.get_channel(814009733006360597)  # type: ignore
                await channel.send(f"Received message '{message}'")
        except Exception as e:
            print(e)

    async def onZMQReceiveREQMessage(self):
        if not self.repSocket:
            return

        try:
            while True:
                try:
                    request = json.loads(await self.repSocket.recv_string())
                except Exception as e:
                    # Probably failed to load since it's an invalid json?
                    request = {}
                    print(e)

                self.dispatch("zmq_request", request)
        except Exception as e:
            print(e)

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
            config = await table.filter(guild_id=guildId).first().values() or {}  # type: ignore

            for i in ("id", "guild_id"):
                config.pop(i, None)
            cached.set(guildId, config)
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
        await self.waitUntilReady()
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
        await self.waitUntilReady()

        await db.Guilds.create(id=guild.id)

        # Cancel deletion
        await self.cancelDeletion(guild)

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Executed when bot leaves a guild"""
        await self.waitUntilReady()
        # Schedule deletion
        await self.scheduleDeletion(guild.id, days=self.guildDelDays)

    async def scheduleDeletion(self, guildId: int, days: int = 30) -> None:
        """Schedule guild deletion from `guilds` table"""
        timer: Timer = self.get_cog("Timer")  # type: ignore
        if not timer:
            return

        now = utcnow()
        when = now + datetime.timedelta(days=days)
        await timer.createTimer(when, "guild_del", created=now, owner=guildId)

    async def cancelDeletion(self, guild: discord.Guild) -> None:
        """Cancel guild deletion"""
        timer: Timer = self.get_cog("Timer")  # type: ignore
        if not timer:
            return

        # Remove the deletion timer and restart timer task
        await db.Timer.filter(owner=guild.id, event="guild_del").delete()

        if timer._currentTimer and timer._currentTimer.owner == guild.id:
            timer.restartTimer()

    async def on_guild_del_timer_complete(self, timer: TimerData) -> None:
        """Executed when guild deletion timer completed"""
        await self.waitUntilReady()
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

    async def processNoNitroEmoji(self, message: discord.Message):
        if message.author.id != 186713080841895936:
            return

        matches = EMOJI_REGEX.findall(message.content)
        if not matches:
            return

        content = message.content

        prefer = {"shuba": 855604899743793152}
        handled = []
        for match in matches:
            if match:
                if match in handled:
                    continue

                prefered = prefer.get(match)
                emoji = None
                if prefered:
                    emoji = discord.utils.get(self.emojis, id=prefered)
                if not emoji:
                    emoji = discord.utils.get(self.emojis, name=match)

                if emoji:
                    content = content.replace(f";{match};", str(emoji))
                handled.append(match)

        await message.reply(content)

    async def process(self, message: discord.Message):
        processed = await self.process_commands(message)
        if not processed:
            return await self.processNoNitroEmoji(message)
        if processed and not isinstance(processed, str):
            self.commandUsage[formatCmdName(processed)] += 1

    async def on_app_command_completion(self, _, command: discord.app_commands.Command | discord.app_commands.ContextMenu):
        self.commandUsage[formatCmdName(command)] += 1

    async def on_message(self, message: discord.Message) -> None:
        if (
            message.author.bot
            or message.author.id in self.blacklist.users
            or (message.guild and message.guild.id in self.blacklist.guilds)
        ) and message.author.id not in self.ownerIds:
            # dont accept commands from bot
            return

        me: discord.ClientUser = self.user  # type: ignore

        # if bot is mentioned without any other message, send prefix list
        guild = GuildWrapper.fromContext(message.guild, self)
        pattern = f"<@(!?){me.id}>"
        if re.fullmatch(pattern, message.content) and guild:
            e = discord.Embed(
                description=await guild.getFormattedPrefixes(),
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
        ) and message.author.id not in self.ownerIds:
            return

        await self.process(message)

    async def waitUntilReady(self):
        if self.config.test:
            return

        await super().wait_until_ready()

    def requireUser(self) -> discord.ClientUser:
        u = self.user
        if not u:
            raise RuntimeError("Bot not ready")
        return u

    async def close(self) -> None:
        """Properly close/turn off bot"""
        if not self.config.test:
            await super().close()

        # Close database connections
        await connections.close_all()
        if self.config.test:
            await Tortoise._drop_databases()

        sockets = (self.pubSocket, self.subSocket, self.repSocket)
        for socket in sockets:
            if not socket:
                continue
            socket.close()

        for task in self.socketTasks:
            task.cancel()

        zmq.asyncio.Context.instance().term()

        # Close aiohttp session
        await self.session.close()

    async def exit(self) -> None:
        await self.close()
        sys.exit(self.exitCode)

    async def run(self) -> None:
        await super().start(self.config.token, reconnect=True)
