import aiohttp
import copy
import datetime
import discord
import os
import logging
import re


from .context import Context
from .errors import CCommandNotFound
from exts.utils import dbQuery
from databases import Database
from discord.ext import commands, tasks


import config


desc = (
    "A **free and open source** multi-purpose **discord bot** created by"
    + " ZiRO2264, formerly called `ziBot`."
)

extensionFolder = "exts"
extensions = []
ignoredExtensions = "youtube.py"
for filename in os.listdir("./{}".format(extensionFolder)):
    if filename in ignoredExtensions:
        continue
    if filename.endswith(".py"):
        extensions.append("{}.{}".format(extensionFolder, filename[:-3]))


def _callable_prefix(bot, message):
    """Callable Prefix for the bot."""
    user_id = bot.user.id
    base = [f"<@!{user_id}> ", f"<@{user_id}> "]
    if not message.guild:
        base.extend(bot.defPrefix)
    else:
        # per-server prefix, soon (TM)
        #   base.extend(
        #       sorted(bot.cache[message.guild.id].get("prefixes", bot.defPrefix))
        #   )

        base.extend(bot.defPrefix)
    return base


class Brain(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=_callable_prefix,
            description=desc,
            case_insensitive=True,
            intents=discord.Intents.all(),
            heartbeat_timeout=150.0,
        )
        # make cogs case insensitive
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()

        # Default colour for embed
        self.colour = discord.Colour(0x3DB4FF)
        self.color = self.colour

        # Bot master(s)
        self.master = (186713080841895936,)

        self.logger = logging.getLogger("discord")

        self.activityIndex = 0

        # bot's default prefix
        self.defPrefix = [">"]

        # database
        self.db = Database(config.sql)

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
        activities = [
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
        ]
        await self.change_presence(activity=activities[self.activityIndex])

        self.activityIndex += 1
        if self.activityIndex > len(activities) - 1:
            self.activityIndex = 0

    async def on_ready(self):
        # change bot's presence into guild live count
        self.changing_presence.start()

        # rows = await self.db.fetch_all("SELECT * FROM commands")
        # print(rows)

        async with self.db.transaction():
            await self.db.execute_many(
                dbQuery.insertToGuilds, values=[{"id": i.id} for i in self.guilds]
            )

        # load all listed extensions
        for extension in extensions:
            self.load_extension(extension)

        if not hasattr(self, 'uptime'):
            self.uptime = datetime.datetime.utcnow()

        self.logger.warning("Ready: {0} (ID: {0.id})".format(self.user))

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=Context)

        if not ctx.prefix:
            return

        # 0 = Built-In, 1 = Custom
        priority = 0
        priorityPrefix = 0
        unixStyle = False
        command = ctx.command

        # Handling custom command priority
        msg = copy.copy(message)
        if ctx.prefix:
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
                command = self.get_command(msgContent[priorityPrefix:])

        # Get arguments for custom commands
        tmp = msgContent[priorityPrefix:].split(" ")
        args = (tmp.pop(0), " ".join(tmp))

        # Check if user can run the command
        canRun = False
        if command:
            try:
                canRun = await command.can_run(ctx)
            except commands.CheckFailure:
                canRun = False

        # Handling command invoke with priority
        if canRun:
            if priority == 1:
                try:
                    # Apparently commands are callable, so ctx.invoke longer needed
                    return await self.get_command("command run")(ctx, *args)
                except CCommandNotFound:
                    # Failed to run custom command, revert to built-in command
                    ctx.command = command
            # Since priority is 0 and it can run the built-in command,
            # no need to try getting custom command
            return await self.invoke(ctx)
        # Priority is 0 but can't run built-in command
        return await self.get_command("command run")(ctx, *args)

    async def on_message(self, message):
        # dont accept commands from bot
        if message.author.bot:
            return

        # if bot is mentioned without any other message, send prefix list
        pattern = f"<@(!?){self.user.id}>"
        if re.fullmatch(pattern, message.content):
            prefixes = _callable_prefix(self, message)
            prefixes.pop(0)
            prefixes.pop(0)
            prefixes = ", ".join([f"`{x}`" for x in prefixes])
            embed = discord.Embed(
                description="My prefixes are: {} or {}".format(
                    prefixes, self.user.mention
                ),
                colour=discord.Colour.rounded(),
            )
            await message.reply(embed=embed)

        await self.process_commands(message)

    async def close(self):
        """Properly close/turn off bot"""
        await super().close()
        # Close database
        # await self.db.close()
        await self.db.disconnect()
        # Close aiohttp session
        await self.session.close()

    def run(self):
        super().run(config.token, reconnect=True)

    @property
    def config(self):
        return __import__("config")
