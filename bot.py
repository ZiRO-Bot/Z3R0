import asyncio
import asyncpg
import aiohttp
import cogs.utils.context as context
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

import config

# Create data directory if its not exist
try:
    os.makedirs("data")
except FileExistsError:
    pass

def get_cogs():
    """callable extensions"""
    extensions = [
        "cogs.welcome",
        "cogs.error_handler",
        "cogs.help",
        "cogs.general",
        "cogs.info",
        "cogs.moderator",
        "cogs.fun",
        "cogs.src",
        "cogs.anilist",
        "cogs.utility",
        "cogs.commands",
        # "cogs.music",
    ]
    return extensions


extensions = get_cogs()

start_time = time.time()


def _callable_prefix(bot, message):
    """Callable Prefix for the bot."""
    user_id = bot.user.id
    base = [f'<@!{user_id}> ', f'<@{user_id}> ']
    if not message.guild:
        base.append(">")
    else:
        base.extend(bot.prefixes.get(message.guild.id, [">"]))
    return base


class ziBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=_callable_prefix,
            case_insensitive=True,
            intents=discord.Intents.all(),
        )
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()

        # Init database
        self.conn = sqlite3.connect("data/database.db")
        self.c = self.conn.cursor()

        self.logger = logging.getLogger("discord")
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.def_prefix = ">"
        self.norules = [758764126679072788, 747984453585993808, 745481731133669476]

        # with open("config.json", "r") as f:
        #     self.config = json.load(f)

        # if not self.config["bot_token"]:
        #     self.logger.error("No token found. Please add it to config.json!")
        #     raise AttributeError("No token found!")

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

        self.loop.create_task(self.async_init())

    async def async_init(self):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Create table to store guild_id
                await conn.execute(
                    """CREATE TABLE IF NOT EXISTS 
                    guilds (guild_id bigint PRIMARY KEY)"""
                )

    def get_guild_prefixes(self, guild, *, local_inject=_callable_prefix):
        proxy_msg = discord.Object(id=0)
        proxy_msg.guild = guild
        return local_inject(self, proxy_msg)

    def get_raw_guild_prefixes(self, guild_id):
        self.bot.c.execute(
            "SELECT prefix FROM servers WHERE (id=?)", (str(guild_id),)
        )
        prefixes = self.bot.c.fetchone()
        return prefixes.split(",")

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

    async def on_ready(self):
        activity = discord.Activity(
            name="over your shoulder", type=discord.ActivityType.watching
        )
        await self.change_presence(activity=activity)

        for extension in extensions:
            self.load_extension(extension)

        self.logger.warning(f"Online: {self.user} (ID: {self.user.id})")

        conn = await self.pool.acquire()
        for guild in self.guilds:
            try:
                async with conn.transaction():
                    await conn.execute(
                        """INSERT INTO guilds 
                        VALUES ($1)""", guild.id
                    )
            except asyncpg.UniqueViolationError:
                pass
        await self.pool.release(conn)
            # self.add_empty_data(server)

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=context.Context)
        can_run = False
        # See if user can run the command (if exists)
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
        
        try:
            await self.invoke(ctx)
        finally:
            # Just in case we have any outstanding DB connections
            await ctx.release() 

    async def on_message(self, message):
        # dont accept commands from bot
        if message.author.bot:
            return
        await self.process_commands(message)

    async def close(self):
        await super().close()
        await self.session.close()

    def run(self):
        super().run(config.token, reconnect=True)

    @property
    def config(self):
        return __import__('config')
