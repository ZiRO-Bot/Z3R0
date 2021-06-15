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
from core.errors import CCommandNotFound, CCommandNotInGuild
from core.objects import Connection
from exts.utils import dbQuery
from databases import Database
from discord.ext import commands, tasks
from typing import Union


import config

DESC = (
    "A **free and open source** multi-purpose **discord bot** created by"
    + " ZiRO2264, formerly called `ziBot`."
)

EXTS = []
EXTS_DIR = "exts"
EXTS_IGNORED = ("twitch.py", "youtube.py", "slash.py", "music.py")
for filename in os.listdir("./{}".format(EXTS_DIR)):
    if filename in EXTS_IGNORED:
        continue
    if filename.endswith(".py"):
        EXTS.append("{}.{}".format(EXTS_DIR, filename[:-3]))


class Blacklist:
    __slots__ = ("filename", "guilds", "users")

    def __init__(self, filename: str = "blacklist.json"):
        self.filename = filename
        data = {}
        try:
            f = open(filename, "r")
            data = json.loads(f.read())
        except FileNotFoundError:
            with open(filename, "w+") as f:
                json.dump(data, f, indent=4)
        self.guilds = data.get("guilds", [])
        self.users = data.get("users", [])

    def __repl__(self):
        return f"<Blacklist: guilds:{self.guilds} users:{self.users}>"

    def dump(self, indent: int = 4, **kwargs):
        temp = "{}-{}.tmp".format(uuid.uuid4(), self.filename)
        data = {"guilds": self.guilds, "users": self.users}
        with open(temp, "w") as tmp:
            json.dump(data.copy(), tmp, indent=indent, **kwargs)

        os.replace(temp, self.filename)
        return True

    def append(self, key: str, value: Union[list, int], **kwargs):
        """Add users/guilds to the blacklist"""
        _type = getattr(self, key)
        if value in _type:
            return

        if isinstance(value, list):
            _type += value
        else:
            try:
                value = int(value)
                _type.append(value)
            except:
                return
        self.dump(**kwargs)
        return value

    def remove(self, key: str, value: int, **kwargs):
        _type = getattr(self, key)
        if value not in _type:
            return

        try:
            value = int(value)
            _type.remove(value)
        except:
            return
        self.dump(**kwargs)
        return value


def _callablePrefix(bot, message):
    """Callable Prefix for the bot."""
    user_id = bot.user.id
    base = [f"<@!{user_id}> ", f"<@{user_id}> "]
    if not message.guild:
        base.extend([bot.defPrefix])
    else:
        # per-server prefix, soon (TM)
        #   base.extend(
        #       sorted(bot.cache[message.guild.id].get("prefixes", [bot.defPrefix]))
        #   )

        base.extend([bot.defPrefix])
    return base


class Brain(commands.Bot):

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
            description=DESC,
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

        # bot's default prefix
        self.defPrefix = ">" if not hasattr(config, "prefix") else config.prefix

        # database
        self.db = Database(config.sql, factory=Connection)

        # async init
        self.loop.create_task(self.asyncInit())
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": "Discord/Z3RO (ziBot/3.0 by ZiRO2264)"}
        )

    async def asyncInit(self):
        """`__init__` but async"""
        # self.db = await aiosqlite.connect("data/database.db")
        await self.db.connect()
        async with self.db.transaction():
            await self.db.execute(dbQuery.createGuildsTable)

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
        await self.change_presence(activity=activities[self.activityIndex])

        self.activityIndex += 1
        if self.activityIndex > len(activities) - 1:
            self.activityIndex = 0

    async def on_ready(self):
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

        # rows = await self.db.fetch_all("SELECT * FROM commands")
        # print(rows)

        async with self.db.transaction():
            await self.db.execute_many(
                dbQuery.insertToGuilds, values=[{"id": i.id} for i in self.guilds]
            )

        if not hasattr(self, "uptime"):
            self.uptime = datetime.datetime.utcnow()

        self.logger.warning("Ready: {0} (ID: {0.id})".format(self.user))

    async def process_commands(self, message):
        # initial ctx
        ctx = await self.get_context(message, cls=Context)

        if not ctx.prefix:
            return

        # 0 = Built-In, 1 = Custom
        priority = 0
        priorityPrefix = 0
        unixStyle = False

        # Handling custom command priority
        msg = copy.copy(message)
        # Get msg content without prefix
        msgContent: str = msg.content[len(ctx.prefix) :]
        if msgContent.startswith(">") or (unixStyle := msgContent.startswith("./")):
            # `./` for unix-style of launching custom scripts
            priority = priorityPrefix = 1
            # Turn `>command` into `command`
            # So it can properly checked
            if unixStyle:
                priorityPrefix = 2
            # Properly get command when priority is 1
            msg.content = ctx.prefix + msgContent[priorityPrefix:]

            # This fixes the problem, idk how ._.
            ctx = await self.get_context(msg, cls=Context)

        # Get arguments for custom commands
        tmp = msgContent[priorityPrefix:].split(" ")
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
            if priority == 1:
                try:
                    await executeCC(*args)
                    self.customCommandUsage += 1
                    return
                except (CCommandNotFound, CCommandNotInGuild):
                    # Failed to run custom command, revert to built-in command
                    return await self.invoke(ctx)
            # Since priority is 0 and it can run the built-in command,
            # no need to try getting custom command
            return await self.invoke(ctx)
        # Can't run built-in command, straight to trying custom command
        await executeCC(*args)
        self.customCommandUsage += 1
        return

    def formattedPrefixes(self, message, codeblock: bool = False):
        prefixes = _callablePrefix(self, message)
        prefixes.pop(0)
        prefixes.pop(0)
        prefixes = ", ".join([f"`{x}`" for x in prefixes])
        return "My prefixes are: {} or {}".format(
            prefixes,
            self.user.mention if not codeblock else ("@" + self.user.display_name),
        )

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
                description=self.formattedPrefixes(message),
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
