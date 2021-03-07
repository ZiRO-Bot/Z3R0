import discord
import os
import logging
import re

from discord.ext import commands, tasks

import config


extensions = []
for filename in os.listdir('./ext'):
    if filename.endswith('.py'):
        extensions.append("ext".format(filename[:-3]))


def _callable_prefix(bot, message):
    """Callable Prefix for the bot."""
    user_id = bot.user.id
    base = [f"<@!{user_id}> ", f"<@{user_id}> "]
    if not message.guild:
        base.extend(bot.def_prefix)
    else:
        # per-server prefix, soon (TM)
        #   base.extend(
        #       sorted(bot.cache[message.guild.id].get("prefixes", bot.def_prefix))
        #   )

        base.extend(bot.def_prefix)
    return base

class ziBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=_callable_prefix,
            case_insensitive=True,
            intents=discord.Intents.all(),
        )
        # make cogs case insensitive
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()

        self.logger = logging.getLogger("discord")

        self.activityIndex = 0
        
        # bot's default prefix
        self.def_prefix = [">"]

    @tasks.loop(seconds=15)
    async def changing_presence(self):
        activities = [
            discord.Activity(
                name=f"over {len(self.guilds)} servers", type=discord.ActivityType.watching
            ),
            discord.Activity(
                name=f"over {len(self.users)} users", type=discord.ActivityType.watching
            ),
            discord.Activity(
                name=f"commands | Ping me to get prefix list!", type=discord.ActivityType.listening
            ),
            discord.Activity(
                name=f"bot war", type=discord.ActivityType.competing
            ),
        ]
        await self.change_presence(activity=activities[self.activityIndex])

        self.activityIndex += 1
        if self.activityIndex > len(activities) - 1:
            self.activityIndex = 0

    async def on_ready(self):
        # change bot's presence into guild live count
        self.changing_presence.start()

        # load all listed extensions
        for extension in extensions:
            self.load_extension(extension)

        self.logger.warning(f"Online: {self.user} (ID: {self.user.id})")

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
            await message.reply("My prefixes are: `{}` or {}".format(prefixes, self.user.mention))

        await self.process_commands(message)

    async def close(self):
        await super().close()

    def run(self):
        super().run(config.token, reconnect=True)

    @property
    def config(self):
        return __import__("config")
