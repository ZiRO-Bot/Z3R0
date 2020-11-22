import asyncio
import asyncpg
import aiohttp
import cogs.utils.context as context
import copy
import datetime
import discord
import json
import logging
import os
import sqlite3
import sys
import traceback

from discord.errors import NotFound
from discord.ext import commands, tasks

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
        "cogs.admin",
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



def _callable_prefix(bot, message):
    """Callable Prefix for the bot."""
    user_id = bot.user.id
    base = [f"<@!{user_id}> ", f"<@{user_id}> "]
    if not message.guild:
        base.append(">")
    else:
        base.extend(sorted(bot.prefixes.get(message.guild.id, [bot.def_prefix])))
    return base


class ziBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=_callable_prefix,
            case_insensitive=True,
            intents=discord.Intents.all(),
        )
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()

        self.start_time = datetime.datetime.utcnow()

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

        # Prefix cache
        self.prefixes = {}

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
        """
        Do database stuff upon init, just incase a table went missing
        or doesn't exist yet.

        Also cache prefix if there's any.
        """

        # Create table if they aren't exists.
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Create table to store guild_id
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS 
                    guilds (
                        id BIGINT PRIMARY KEY
                    )
                    """
                )
                # Table for prefixes, will no longer use ',' separator
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS 
                    prefixes (
                        guild_id BIGINT REFERENCES guilds(id) ON DELETE CASCADE NOT NULL,
                        prefix TEXT NOT NULL
                    )
                    """
                )

                # Prefix cache
                pre = [(i, p) for i, p in await conn.fetch("SELECT * FROM prefixes")]
                for k, v in pre:
                    self.prefixes[k] = self.prefixes.get(k, []) + [v]
    
    @tasks.loop(minutes=2)
    async def changing_presence(self):
        activity = discord.Activity(
            name=f"over {len(self.guilds)} servers", type=discord.ActivityType.watching
        )
        await self.change_presence(activity=activity)


    def get_guild_prefixes(self, guild, *, local_inject=_callable_prefix):
        proxy_msg = discord.Object(id=0)
        proxy_msg.guild = guild
        return local_inject(self, proxy_msg)

    async def get_raw_guild_prefixes(self, connection, guild_id: int):
        prefixes = [
            pre
            for pre, in await connection.fetch(
                "SELECT prefix FROM prefixes WHERE (guild_id=$1)", guild_id
            )
        ]
        return prefixes

    async def bulk_remove_guild_prefixes(self, connection, guild_id, prefixes):
        async with connection.transaction():
            await connection.executemany(
                "DELETE FROM prefixes WHERE guild_id=$1 AND prefix=$2",
                [(guild_id, p) for p in prefixes],
            )
        if guild_id in self.prefixes:
            for p in prefixes:
                self.prefixes[guild_id].remove(p)

    async def add_guild_prefix(self, connection, guild_id, prefix):
        async with connection.transaction():
            await connection.execute(
                "INSERT INTO prefixes VALUES($1, $2)", guild_id, prefix
            )
        if guild_id in self.prefixes:
            self.prefixes[guild_id] += [prefix]
        else:
            self.prefixes[guild_id] = [prefix]

    async def bulk_add_guild_prefixes(self, connection, guild_id, prefixes):
        async with connection.transaction():
            await connection.executemany(
                "INSERT INTO prefixes VALUES($1, $2)", [(guild_id, p) for p in prefixes]
            )
        if guild_id in self.prefixes:
            self.prefixes[guild_id] += prefixes
        else:
            self.prefixes[guild_id] = prefixes

    async def add_guild_id(self, connection, guild):
        try:
            async with connection.transaction():
                await connection.execute(
                    """INSERT INTO guilds 
                    VALUES ($1)""",
                    guild.id,
                )
        except asyncpg.UniqueViolationError:
            return

    async def remove_guild_id(self, connection, guild):
        try:
            async with connection.transaction():
                await connection.execute(
                    """DELETE FROM guilds 
                    WHERE guild_id=$1""",
                    guild.id,
                )
        except asyncpg.UniqueViolationError:
            return

    async def on_guild_join(self, guild):
        conn = await self.pool.acquire()
        await self.add_guild_id(conn, guild)
        if guild.id not in self.prefixes:
            await self.add_guild_prefix(conn, guild.id, self.def_prefix)
        await self.pool.release(conn)

    async def on_guild_remove(self, guild):
        conn = await self.pool.acquire()
        await self.remove_guild_id(conn, guild)
        await self.pool.release(conn)

    async def on_ready(self):
        self.changing_presence.start()
        for extension in extensions:
            self.load_extension(extension)

        self.logger.warning(f"Online: {self.user} (ID: {self.user.id})")

        conn = await self.pool.acquire()
        for guild in self.guilds:
            await self.add_guild_id(conn, guild)
            if guild.id not in self.prefixes:
                await self.add_guild_prefix(conn, guild.id, self.def_prefix)
        await self.pool.release(conn)

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
        return __import__("config")
