import aiohttp
import copy
import discord
import json
import logging
import os
import sqlite3
import sys
import traceback
import time

from discord.errors import NotFound
from discord.ext import commands
from dotenv import load_dotenv

# Create data directory if its not exist
try:
    os.makedirs("data")
except FileExistsError:
    pass

try:
    token = os.environ("TOKEN")
except:
    load_dotenv()
    token = os.getenv("TOKEN")

shard = os.getenv("SHARD") or 0
shard_count = os.getenv("SHARD_COUNT") or 1


def get_cogs():
    """callable extensions"""
    extensions = [
        "cogs.welcome",
        "cogs.error_handler",
        "cogs.help",
        "cogs.general",
        "cogs.moderator",
        "cogs.fun",
        "cogs.src",
        "cogs.anilist",
        "cogs.utils",
        "cogs.custom_commands",
        # "cogs.music",
    ]
    return extensions


extensions = get_cogs()

start_time = time.time()


def get_prefix(bot, message):
    """A callable Prefix for our bot. This could be edited to allow per server prefixes."""
    base = []
    if not message.guild:
        base.append(">")
    else:
        base.extend(bot.prefixes.get(message.guild.id, [">"]))
    return base


class ziBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Init database
        self.conn = sqlite3.connect("data/database.db")
        self.c = self.conn.cursor()

        self.c.execute("SELECT * FROM servers WHERE 1")
        servers_row = self.c.fetchall()
        pre = {k[0]: k[1] or ">" for k in servers_row}
        self.prefixes = {int(k): v.split(",") for (k, v) in pre.items()}

        self.logger = logging.getLogger("discord")
        self.session = aiohttp.ClientSession()
        self.def_prefix = ">"
        self.norules = [758764126679072788, 747984453585993808, 745481731133669476]

        with open("config.json", "r") as f:
            self.config = json.load(f)

        if not self.config["bot_token"]:
            self.logger.error("No token found. Please add it to config.json!")
            raise AttributeError("No token found!")

        # Create "servers" table if its not exists
        self.c.execute(
            """CREATE TABLE IF NOT EXISTS servers
                (id text unique, prefixes text, anime_ch int, 
                greeting_ch int, meme_ch int, purge_ch int,
                pingme_ch int, announcement_ch int)"""
        )
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
    
    def set_guild_prefixes(self, guild, prefixes):
        if not prefixes:
            self.c.execute('UPDATE servers SET prefix=? WHERE id=?',
                      (None, guild.id))
            self.conn.commit()
            self.prefixes[guild.id] = prefixes
        elif len(prefixes) > 15:
            raise RuntimeError('You can only add up to 15 prefixes.')
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

    async def on_ready(self):
        activity = discord.Activity(
            name="over your shoulder", type=discord.ActivityType.watching
        )
        await self.change_presence(activity=activity)

        for extension in extensions:
            self.load_extension(extension)

        self.logger.warning(f"Online: {self.user} (ID: {self.user.id})")

        for server in self.guilds:
            self.add_empty_data(server)

    async def on_message(self, message):
        # dont accept commands from bot
        if message.author.bot:
            return

        await self.process_commands(message)

        ctx = await self.get_context(message)
        if (
            ctx.invoked_with
            and ctx.invoked_with.lower() not in self.commands
            and ctx.command is None
        ):
            msg = copy.copy(message)
            if ctx.prefix:
                new_content = msg.content[len(ctx.prefix) :]
                msg.content = "{}tag get {}".format(ctx.prefix, new_content)
                await self.process_commands(msg)

    async def close(self):
        await super().close()
        await self.session.close()

    def run(self):
        super().run(self.config["bot_token"], reconnect=True)
