import aiohttp
import discord
import json
import logging
import os
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

    with open("data/guild.json", "r") as f:
        prefixes = json.load(f)

    if prefixes[str(message.guild.id)]["mention_as_prefix"]:
        return commands.when_mentioned_or(*prefixes[str(message.guild.id)]["prefix"])(
            bot, message
        )
    return prefixes[str(message.guild.id)]["prefix"]


class ziBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger = logging.getLogger("discord")
        self.session = aiohttp.ClientSession()
        self.def_prefix = ">"

        self.master = [186713080841895936]

        check_jsons()

        with open('data/anime.json', 'r') as wl:
            self.watchlist = json.load(wl)

        with open("data/custom_commands.json", "r") as cc:
            self.custom_commands = json.load(cc)

        with open("data/guild.json", "r") as ch:
            self.config = json.load(ch)

    async def on_guild_join(self, guild):
        with open("data/guild.json", "w") as f:
            self.config[str(guild.id)] = {}
            self.config[str(guild.id)]["mention_as_prefix"] = False
            self.config[str(guild.id)]["prefix"] = [self.def_prefix]

            json.dump(self.config, f, indent=4)
        
        with open('data/anime.json', 'w') as f:
            watchlist[str(guild.id)] = []
            json.dump(watchlist, f, indent=4)

    async def on_guild_remove(self, guild):
        with open("data/guild.json", "w") as f:
            del self.config[str(guild.id)]

            json.dump(self.config, f, indent=4)

    async def on_ready(self):
        activity = discord.Activity(
            name="over your shoulder", type=discord.ActivityType.watching
        )
        await self.change_presence(activity=activity)

        for extension in extensions:
            self.load_extension(extension)

        self.logger.warning(f"Online: {self.user} (ID: {self.user.id})")

    async def on_message(self, message):
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
