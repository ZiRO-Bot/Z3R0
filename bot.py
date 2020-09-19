import aiohttp
import discord
import json
import logging
import os
import sqlite3
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


def check_jsons():
    try:
        f = open("data/guild.json", "r")
    except FileNotFoundError:
        with open("data/guild.json", "w+") as f:
            json.dump({}, f, indent=4)

    try:
        f = open("data/custom_commands.json", "r")
    except FileNotFoundError:
        with open("data/custom_commands.json", "w+") as f:
            json.dump({}, f, indent=4)

    try:
        f = open("data/anime.json", "r")
    except FileNotFoundError:
        with open("data/anime.json", "w+") as f:
            json.dump({"watchlist": []}, f, indent=4)


def get_cogs():
    """callable extensions"""
    extensions = [
        "cogs.welcome",
        "cogs.help",
        "cogs.moderator",
        "cogs.general",
        "cogs.utils",
        "cogs.mcbe",
        "cogs.anilist",
        "cogs.fun",
        # "cogs.music",
    ]
    return extensions


extensions = get_cogs()

start_time = time.time()


def get_prefix(bot, message):
    """A callable Prefix for our bot. This could be edited to allow per server prefixes."""

    bot.c.execute("SELECT * FROM servers WHERE (id=?)", (str(message.guild.id),))
    servers_row = bot.c.fetchall()
    pre = {k[0]: k[1] or ">" for k in servers_row}
    prefixes = {int(k): v.split(",") for (k, v) in pre.items()}

    return prefixes[message.guild.id]


class ziBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger = logging.getLogger("discord")
        self.session = aiohttp.ClientSession()
        self.def_prefix = ">"

        # Init database
        self.conn = sqlite3.connect("data/database.db")
        self.c = self.conn.cursor()
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

        self.master = [186713080841895936]

        check_jsons()

        with open("data/custom_commands.json", "r") as cc:
            self.custom_commands = json.load(cc)

        # with open("data/guild.json", "r") as ch:
        #     self.config = json.load(ch)

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

        try:
            command = message.content.split()[0]
        except IndexError:
            pass

        try:
            if command in self.custom_commands[str(message.guild.id)]:
                await message.channel.send(
                    self.custom_commands[str(message.guild.id)][command]
                )
                return
        except:
            return

    def run(self):
        super().run(token, reconnect=True)
