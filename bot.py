import aiohttp
import discord
import json
import logging
import os

from discord.ext import commands
from dotenv import load_dotenv

try:
    token = os.environ('TOKEN')
except:
    load_dotenv()
    token = os.getenv('TOKEN')

shard = os.getenv('SHARD') or 0
shard_count = os.getenv('SHARD_COUNT') or 1

def check_jsons():
    try:
        f = open('data/guild.json', 'r')
    except FileNotFoundError:
        with open('data/guild.json', 'w+') as f:
            json.dump({"0": {}}, f, indent=4)

def get_cogs():
    """callable extensions"""
    extensions = [
	              "cogs.welcome", "cogs.help", "cogs.moderator",
                  "cogs.general", "cogs.utils", "cogs.mcbe",
                  "cogs.anilist", "cogs.fun"
                 ]
    return extensions

extensions = get_cogs() 

def get_prefix():
	"""A callable Prefix for our bot. This could be edited to allow per server prefixes."""

	prefixes = ['>', '$>', '.']

	# Check to see if we are outside of a guild. e.g DM's etc.
	# if not message.guild:
	# Only allow ? to be used in DMs
	#   return '?'

	# If we are in a guild, we allow for the user to mention us or use any of the prefixes in our list.
	return prefixes

class ziBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger = logging.getLogger('discord')
        self.session = aiohttp.ClientSession()
         
        check_jsons()

        with open('custom_commands.json', 'r') as cc:
            self.custom_commands = json.load(cc)

        with open('data/guild.json', 'r') as ch:
            self.channels = json.load(ch)

    async def on_ready(self): 
        activity=discord.Activity(name="over your shoulder",type=discord.ActivityType.watching)
        await self.change_presence(activity=activity)

        for extension in extensions:
            self.load_extension(extension)
        
        self.logger.warning(f'Online: {self.user} (ID: {self.user.id})')

    async def on_message(self, message):
        await self.process_commands(message)

        try:
            command = message.content.split()[0]
        except IndexError:
            pass
        
        try:
            if command in self.custom_commands:
                await message.channel.send(self.custom_commands[command])
                return
        except:
            return

    def run(self):
        super().run(token, reconnect=True)
