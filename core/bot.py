import asyncio
import aiohttp
import copy
import discord
import json
import logging
import os
import re
import sqlite3
import sys
import traceback
import time

from cogs.utilities.tse_blocks import DiscordMemberBlock, DiscordGuildBlock
from discord.errors import NotFound
from discord.ext import commands, tasks
from TagScriptEngine import Interpreter, block

# Create data directory if its not exist
try:
    os.makedirs("data")
except FileExistsError:
    pass


EXTS = []
EXTS_DIR = "cogs"
EXTS_IGNORED = (
    "admin.py",
    "youtube.py",
    "twitch.py",
    "slash.py",
    "src.py",
    "mcbe.py",
    "music.py",
)
for filename in os.listdir("./{}".format(EXTS_DIR)):
    if filename in EXTS_IGNORED:
        continue
    if filename.endswith(".py"):
        EXTS.append("{}.{}".format(EXTS_DIR, filename[:-3]))


start_time = time.time()


def _callable_prefix(bot, message):
    """A callable Prefix for our bot. This could be edited to allow per server prefixes."""
    user_id = bot.user.id
    base = [f"<@!{user_id}> ", f"<@{user_id}> "]
    if not message.guild:
        base.append(">")
    else:
        base.extend(bot.prefixes.get(message.guild.id, [">"]))
    return base


get_prefix = _callable_prefix


class ziBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=_callable_prefix,
            case_insensitive=True,
            allowed_mentions=discord.AllowedMentions(users=True, roles=False),
            intents=discord.Intents.all(),
        )
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()

        self.version = "2.2.A"

        self.blocks = [block.RandomBlock(), block.StrictVariableGetterBlock()]

        self.activityIndex = 0

        # Init database
        self.conn = sqlite3.connect("data/database.db")
        self.c = self.conn.cursor()

        self.logger = logging.getLogger("discord")
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.def_prefix = ">"
        self.norules = [758764126679072788, 747984453585993808, 745481731133669476]

        with open("config.json", "r") as f:
            self.config = json.load(f)

        if not self.config["bot_token"]:
            self.logger.error("No token found. Please add it to config.json!")
            raise AttributeError("No token found!")

        # Create tables
        self.c.execute(
            """CREATE TABLE IF NOT EXISTS servers
                (id text unique, prefixes text, anime_ch int,
                greeting_ch int, meme_ch int, purge_ch int,
                pingme_ch int, announcement_ch int)"""
        )
        self.c.execute("SELECT * FROM servers WHERE 1")
        servers_row = self.c.fetchall()
        pre = {k[0]: k[1] or ">" for k in servers_row}
        self.prefixes = {int(k): v.split(",") for (k, v) in pre.items()}

        self.c.execute(
            """CREATE TABLE IF NOT EXISTS ani_watchlist
                (id text unique, anime_id text)"""
        )
        self.c.execute(
            """CREATE TABLE IF NOT EXISTS roles
                (id text unique, default_role int, mute_role int)"""
        )
        self.c.execute(
            """CREATE TABLE IF NOT EXISTS settings
                (id text unique, send_error_msg int,
                disabled_cmds text, welcome_msg text,
                farewell_msg text, mods_only text)"""
        )

        self.master = [186713080841895936]

        self.loop.create_task(self.start_up())

    async def start_up(self):
        await self.wait_until_ready()

        self.changing_presence.start()

        for server in self.guilds:
            self.add_empty_data(server)

    def init_tagscript(
        self,
        blocks: list = None,
        member: discord.Member = None,
        guild: discord.Guild = None,
        context: commands.Context = None,
    ):
        if not blocks:
            blocks = self.blocks
        if member:
            blocks += [DiscordMemberBlock(member, context)]
        if guild:
            blocks += [DiscordGuildBlock(guild, context)]
        return Interpreter(blocks)

    def set_guild_prefixes(self, guild, prefixes):
        if not prefixes:
            self.c.execute("UPDATE servers SET prefix=? WHERE id=?", (None, guild.id))
            self.conn.commit()
            self.prefixes[guild.id] = prefixes
        elif len(prefixes) > 15:
            raise RuntimeError("You can only add up to 15 prefixes.")
        else:
            self.c.execute(
                "UPDATE servers SET prefixes = ? WHERE id = ?",
                (",".join(sorted(prefixes)), str(guild.id)),
            )
            self.conn.commit()
            self.prefixes[guild.id] = sorted(set(prefixes))

    def add_empty_data(self, guild):
        # guild_id, prefix, anime_ch, greeting_ch, meme_ch, purge_ch
        self.c.execute(
            """INSERT OR IGNORE INTO servers
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(guild.id), self.def_prefix, None, None, None, None, None, None),
        )
        self.conn.commit()
        self.c.execute(
            """INSERT OR IGNORE INTO ani_watchlist
            VALUES (?, ?)""",
            (str(guild.id), None),
        )
        self.conn.commit()
        self.c.execute(
            """INSERT OR IGNORE INTO roles
            VALUES (?, ?, ?)""",
            (str(guild.id), None, None),
        )
        self.conn.commit()
        self.c.execute(
            """INSERT OR IGNORE INTO settings
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                str(guild.id),
                0,
                None,
                None,
                None,
                "command add,command edit,command remove",
            ),
        )
        self.conn.commit()

    def remove_guild_data(self, guild):
        self.c.execute(
            """DELETE FROM servers
            WHERE id=?""",
            (str(guild.id),),
        )
        self.conn.commit()
        self.c.execute(
            """DELETE FROM ani_watchlist
            WHERE id=?""",
            (str(guild.id),),
        )
        self.conn.commit()
        self.c.execute(
            """DELETE FROM roles
            WHERE id=?""",
            (str(guild.id),),
        )
        self.conn.commit()
        self.c.execute(
            """DELETE FROM settings
            WHERE id=?""",
            (str(guild.id),),
        )
        self.conn.commit()

    async def on_guild_join(self, guild):
        self.add_empty_data(guild)

    async def on_guild_remove(self, guild):
        self.remove_guild_data(guild)

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
        self.logger.warning(f"Online: {self.user} (ID: {self.user.id})")

    async def process_commands(self, message):
        ctx = await self.get_context(message)

        # See if user can run the command (if exists)
        can_run = False
        if ctx.command:
            try:
                can_run = await ctx.command.can_run(ctx)
            except commands.CheckFailure:
                can_run = False

        if (
            ctx.invoked_with
            and ctx.invoked_with.lower() not in self.commands
            and (not ctx.command or not can_run)
        ):
            msg = copy.copy(message)
            if ctx.prefix:
                new_content = msg.content[len(ctx.prefix) :]
                msg.content = "{}tag get {}".format(ctx.prefix, new_content)
                return await self.process_commands(msg)

        await self.invoke(ctx)

    async def on_message(self, message):
        # dont accept commands from bot
        if message.author.bot:
            return

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
        await super().close()
        await self.session.close()

    def run(self):
        for extension in EXTS:
            self.load_extension(extension)

        super().run(self.config["bot_token"], reconnect=True)
